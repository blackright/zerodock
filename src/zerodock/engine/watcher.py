"""Application-owned, exact-path content polling for development handlers."""

import asyncio
import hashlib
import logging
import math
from collections.abc import Iterable
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeVar

from zerodock.engine.loader import (
    handler_module_name,
    invalidate_handler_cache,
    watch_handler_cache,
)

logger = logging.getLogger("uvicorn.error.zerodock.reload")
_Result = TypeVar("_Result")


@dataclass(frozen=True)
class ObservedRevision:
    status: Literal["readable", "missing", "unreadable"]
    digest: str | None = None
    error_category: str | None = None


def read_revisions(paths: tuple[Path, ...]) -> dict[Path, ObservedRevision]:
    """Read fingerprints only; never execute source or mutate module state."""
    revisions = {}
    for path in paths:
        try:
            digest = hashlib.sha256()
            with path.open("rb") as source:
                while chunk := source.read(65536):
                    digest.update(chunk)
            revisions[path] = ObservedRevision("readable", digest.hexdigest())
        except FileNotFoundError:
            revisions[path] = ObservedRevision("missing")
        except OSError as exc:
            revisions[path] = ObservedRevision("unreadable", error_category=type(exc).__name__)
    return revisions


async def _await_completion(task: asyncio.Task[_Result]) -> _Result:
    interrupted = False
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            interrupted = True
        except Exception:
            break
    if interrupted:
        if not task.cancelled():
            task.exception()
        raise asyncio.CancelledError
    return task.result()


class HandlerWatcher:
    """Observe configured targets without restarting the gateway process."""

    def __init__(self, paths: Iterable[Path], *, interval: float = 0.1) -> None:
        if not math.isfinite(interval) or interval <= 0:
            raise ValueError("Polling interval must be finite and positive")
        self.paths = tuple(sorted({Path(path).resolve() for path in paths}))
        self.interval = interval
        self.revisions: dict[Path, ObservedRevision] = {}
        self.task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()
        self._scan_lock = asyncio.Lock()
        self._lifecycle_lock = asyncio.Lock()
        self._shutdown_task: asyncio.Task[None] | None = None
        self._failure_reported = False
        self._owners = ExitStack()

    async def _observe(self) -> dict[Path, ObservedRevision]:
        pending = asyncio.create_task(asyncio.to_thread(read_revisions, self.paths))
        return await _await_completion(pending)

    def _invalidate_revision(self, path: Path, revision: ObservedRevision) -> None:
        module_name = handler_module_name(path)
        invalidate_handler_cache(module_name)
        if revision.status == "readable":
            logger.info("Invalidated handler %s", module_name)
        else:
            category = f" ({revision.error_category})" if revision.error_category else ""
            logger.warning("Handler source %s is %s%s", path, revision.status, category)

    async def scan_once(self) -> tuple[Path, ...]:
        """Reconcile one serialized scan and acknowledge invalidated paths."""
        async with self._scan_lock:
            if self._stop.is_set():
                return ()
            observed = await self._observe()
            if self._stop.is_set():
                return ()
            changed = []
            for path, revision in observed.items():
                previous = self.revisions.get(path)
                if previous == revision:
                    continue
                self._invalidate_revision(path, revision)
                changed.append(path)
            self.revisions = observed
            return tuple(changed)

    async def start(self) -> None:
        """Register ownership and reconcile startup edits before observation."""
        async with self._lifecycle_lock:
            if self._shutdown_task is not None and not self._shutdown_task.done():
                raise RuntimeError("Handler watcher is stopping")
            if self.task is not None:
                raise RuntimeError("Handler watcher is already running")
            self._shutdown_task = None
            self._failure_reported = False
            self._stop.clear()
            try:
                for path in self.paths:
                    self._owners.enter_context(watch_handler_cache(handler_module_name(path)))
                async with self._scan_lock:
                    self.revisions = await self._observe()
                    if self._stop.is_set():
                        raise RuntimeError("Handler watcher stopped during startup")
                    for path, revision in self.revisions.items():
                        if revision.status != "readable":
                            self._invalidate_revision(path, revision)
                await self.scan_once()
                if self._stop.is_set():
                    raise RuntimeError("Handler watcher stopped during startup")
                self.task = asyncio.create_task(self._run(), name="zerodock-handler-reload")
                self.task.add_done_callback(self._report_failure)
                logger.info("Reload enabled for %d handler file(s)", len(self.paths))
                for path in self.paths:
                    logger.debug("Watching handler %s", path)
            except BaseException:
                self._stop.set()
                cleanup = asyncio.create_task(
                    self._cleanup(), name="zerodock-handler-reload-startup-cleanup"
                )
                try:
                    await _await_completion(cleanup)
                except asyncio.CancelledError:
                    pass
                except Exception:
                    logger.exception("Handler reload startup cleanup failed")
                raise

    def _report_failure(self, task: asyncio.Task[None]) -> None:
        if self._failure_reported:
            return
        if task.cancelled():
            if self._stop.is_set():
                return
            self._failure_reported = True
            logger.error("Handler reload observer was cancelled unexpectedly")
            return
        error = task.exception()
        if error is not None:
            self._failure_reported = True
            logger.error(
                "Handler reload observer stopped unexpectedly",
                exc_info=(type(error), error, error.__traceback__),
            )
        elif not self._stop.is_set():
            self._failure_reported = True
            logger.error("Handler reload observer stopped unexpectedly without a stop request")

    async def _wait_for_poll(self) -> bool:
        try:
            await asyncio.wait_for(self._stop.wait(), timeout=self.interval)
        except asyncio.TimeoutError:
            return True
        return False

    async def _run(self) -> None:
        while await self._wait_for_poll():
            await self.scan_once()

    async def _cleanup(self) -> None:
        try:
            if self.task is not None:
                try:
                    await _await_completion(self.task)
                except (asyncio.CancelledError, Exception):
                    self._report_failure(self.task)
            async with self._scan_lock:
                pass
        finally:
            self._owners.close()
            self.task = None

    async def _stop_serialized(self) -> None:
        async with self._lifecycle_lock:
            await self._cleanup()

    async def stop(self) -> None:
        """Drain owned work even if a caller cancels its shutdown wait.

        Filesystem calls cannot be forcibly interrupted, so shutdown may wait
        indefinitely on a stalled filesystem. The shared executor is not closed.
        """
        if self.task is not None and self.task.done():
            self._report_failure(self.task)
        self._stop.set()
        if self._shutdown_task is None or self._shutdown_task.done():
            self._shutdown_task = asyncio.create_task(
                self._stop_serialized(), name="zerodock-handler-reload-stop"
            )
        await _await_completion(self._shutdown_task)
