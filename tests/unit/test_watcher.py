"""Deterministic content-observation tests for handler reload."""

import asyncio
import hashlib
import importlib
import logging
import os
import sys
import threading
from contextlib import contextmanager, suppress
from pathlib import Path

import pytest

from zerodock.engine import loader


@pytest.fixture
def watcher_module():
    return importlib.import_module("zerodock.engine.watcher")


@pytest.mark.asyncio
async def test_watcher_deduplicates_canonical_targets(handler_factory, watcher_module):
    file_path = handler_factory("def handler(event): return 'A'\n")
    watcher = watcher_module.HandlerWatcher([file_path, file_path.parent / "." / file_path.name])
    assert watcher.interval == 0.1
    assert watcher.paths == (file_path,)
    assert watcher.task is None
    await watcher.start()
    try:
        revision = watcher.revisions[file_path]
        assert revision.status == "readable"
        assert revision.digest == hashlib.sha256(file_path.read_bytes()).hexdigest()
        state = loader._module_states[loader.handler_module_name(file_path)]
        assert state.watcher_owners == 1
    finally:
        await watcher.stop()
    assert watcher.task is None
    assert loader.handler_module_name(file_path) not in loader._module_states


@pytest.mark.asyncio
async def test_watcher_detects_same_metadata_edit_once(
    handler_factory, watcher_module, monkeypatch, caplog
):
    file_path = handler_factory("def handler(event): return 'A'\n")
    original_stat = file_path.stat()
    invalidations = []
    original_invalidate = loader.invalidate_handler_cache

    def invalidate(module_name):
        invalidations.append(module_name)
        original_invalidate(module_name)

    monkeypatch.setattr(watcher_module, "invalidate_handler_cache", invalidate)
    watcher = watcher_module.HandlerWatcher([file_path], interval=60)
    with caplog.at_level(logging.INFO, logger="uvicorn.error.zerodock.reload"):
        await watcher.start()
        try:
            assert await watcher.scan_once() == ()
            file_path.write_text("def handler(event): return 'B'\n", encoding="utf-8")
            os.utime(file_path, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
            assert await watcher.scan_once() == (file_path,)
            assert await watcher.scan_once() == ()
        finally:
            await watcher.stop()
    assert invalidations == [loader.handler_module_name(file_path)]
    assert "Reload enabled" in caplog.text
    assert "Invalidated handler" in caplog.text
    assert "return 'B'" not in caplog.text


@pytest.mark.asyncio
async def test_watcher_coalesces_saves_and_ignores_unrelated_files(handler_factory, watcher_module):
    file_path = handler_factory("def handler(event): return 'A'\n")
    unrelated = handler_factory("value = 1\n", "unrelated.py")
    watcher = watcher_module.HandlerWatcher([file_path], interval=60)
    await watcher.start()
    try:
        unrelated.write_text("value = 2\n", encoding="utf-8")
        assert await watcher.scan_once() == ()
        for version in ("B", "C", "D"):
            file_path.write_text(f"def handler(event): return '{version}'\n", encoding="utf-8")
        assert await watcher.scan_once() == (file_path,)
        expected_digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
        assert watcher.revisions[file_path].digest == expected_digest
        assert await watcher.scan_once() == ()
    finally:
        await watcher.stop()


@pytest.mark.asyncio
async def test_scan_runs_off_loop_without_overlapping_workers(
    handler_factory, watcher_module, scan_barrier, monkeypatch
):
    file_path = handler_factory("def handler(event): return 'A'\n")
    watcher = watcher_module.HandlerWatcher([file_path], interval=60)
    await watcher.start()
    original_read = watcher_module.read_revisions
    active = 0
    maximum = 0
    worker_ids = []
    guard = threading.Lock()

    def blocked_read(paths):
        nonlocal active, maximum
        with guard:
            active += 1
            maximum = max(maximum, active)
            worker_ids.append(threading.get_ident())
        try:
            scan_barrier.wait()
            return original_read(paths)
        finally:
            with guard:
                active -= 1

    monkeypatch.setattr(watcher_module, "read_revisions", blocked_read)
    first = asyncio.create_task(watcher.scan_once())
    second = None
    try:
        assert await asyncio.to_thread(scan_barrier.entered.wait, 5)
        second = asyncio.create_task(watcher.scan_once())
        await asyncio.sleep(0)
        scan_barrier.release.set()
        await asyncio.gather(first, second)
        assert maximum == 1
        assert all(worker_id != threading.get_ident() for worker_id in worker_ids)
    finally:
        scan_barrier.release.set()
        await asyncio.gather(first, *([second] if second is not None else []))
        await watcher.stop()


@pytest.mark.asyncio
async def test_startup_reconciliation_does_not_swallow_an_edit(
    handler_factory, watcher_module, monkeypatch
):
    file_path = handler_factory("def handler(event): return 'A'\n")
    original_read = watcher_module.read_revisions
    reads = 0

    def read_and_edit(paths):
        nonlocal reads
        result = original_read(paths)
        reads += 1
        if reads == 1:
            file_path.write_text("def handler(event): return 'B'\n", encoding="utf-8")
        return result

    load_handler = loader.load_handler(file_path, "handler")
    assert load_handler({}) == "A"
    monkeypatch.setattr(watcher_module, "read_revisions", read_and_edit)
    watcher = watcher_module.HandlerWatcher([file_path], interval=60)
    await watcher.start()
    try:
        assert reads == 2
        assert loader.handler_module_name(file_path) not in sys.modules
        expected_digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
        assert watcher.revisions[file_path].digest == expected_digest
    finally:
        await watcher.stop()


@pytest.mark.parametrize("interval", [0, -0.1])
def test_watcher_rejects_nonpositive_interval(watcher_module, interval):
    with pytest.raises(ValueError, match="positive"):
        watcher_module.HandlerWatcher([], interval=interval)


@pytest.mark.asyncio
async def test_atomic_replacement_refreshes_only_configured_path(handler_factory, watcher_module):
    file_path = handler_factory("def handler(event): return 'A'\n")
    replacement = handler_factory("def handler(event): return 'B'\n", "pending.py")
    watcher = watcher_module.HandlerWatcher([file_path], interval=60)
    await watcher.start()
    try:
        replacement.replace(file_path)
        assert await watcher.scan_once() == (file_path,)
        assert watcher.paths == (file_path,)
        assert loader.load_handler(file_path, "handler", reload=True)({}) == "B"
        assert await watcher.scan_once() == ()
    finally:
        await watcher.stop()


@pytest.mark.asyncio
async def test_deletion_invalidates_once_and_recreation_recovers(handler_factory, watcher_module):
    file_path = handler_factory("def handler(event): return 'A'\n")
    watcher = watcher_module.HandlerWatcher([file_path], interval=60)
    await watcher.start()
    try:
        loader.load_handler(file_path, "handler", reload=True)
        file_path.unlink()
        assert await watcher.scan_once() == (file_path,)
        assert watcher.revisions[file_path].status == "missing"
        assert loader.handler_module_name(file_path) not in sys.modules
        assert await watcher.scan_once() == ()
        file_path.write_text("def handler(event): return 'B'\n", encoding="utf-8")
        assert await watcher.scan_once() == (file_path,)
        assert loader.load_handler(file_path, "handler", reload=True)({}) == "B"
    finally:
        await watcher.stop()


@pytest.mark.asyncio
async def test_unreadable_source_invalidates_without_repeated_logs(
    handler_factory, watcher_module, monkeypatch, caplog
):
    file_path = handler_factory("def handler(event): return 'A'\n")
    watcher = watcher_module.HandlerWatcher([file_path], interval=60)
    original_open = Path.open

    def denied(path, *args, **kwargs):
        if path == file_path:
            raise PermissionError("SOURCE_SECRET_NOT_FOR_LOGGING")
        return original_open(path, *args, **kwargs)

    await watcher.start()
    try:
        loader.load_handler(file_path, "handler", reload=True)
        with caplog.at_level(logging.WARNING, logger="uvicorn.error.zerodock.reload"):
            with monkeypatch.context() as patch:
                patch.setattr(Path, "open", denied)
                assert await watcher.scan_once() == (file_path,)
                assert watcher.revisions[file_path].status == "unreadable"
                assert watcher.revisions[file_path].error_category == "PermissionError"
                assert loader.handler_module_name(file_path) not in sys.modules
                assert await watcher.scan_once() == ()
            assert len(caplog.records) == 1
            assert "SOURCE_SECRET_NOT_FOR_LOGGING" not in caplog.text
        assert await watcher.scan_once() == (file_path,)
        assert loader.load_handler(file_path, "handler", reload=True)({}) == "A"
    finally:
        await watcher.stop()


@pytest.mark.asyncio
async def test_startup_unreadable_target_warns_once(
    handler_factory, watcher_module, monkeypatch, caplog
):
    file_path = handler_factory("value = 1\n")
    revision = watcher_module.ObservedRevision("unreadable", error_category="PermissionError")
    monkeypatch.setattr(watcher_module, "read_revisions", lambda paths: {file_path: revision})
    watcher = watcher_module.HandlerWatcher([file_path], interval=60)
    with caplog.at_level(logging.WARNING, logger="uvicorn.error.zerodock.reload"):
        await watcher.start()
        try:
            assert await watcher.scan_once() == ()
        finally:
            await watcher.stop()
    assert len(caplog.records) == 1
    assert "unreadable" in caplog.text


@pytest.mark.asyncio
async def test_error_category_changes_are_logged_once_per_transition(
    handler_factory, watcher_module, monkeypatch, caplog
):
    file_path = handler_factory("value = 1\n")
    watcher = watcher_module.HandlerWatcher([file_path], interval=60)
    await watcher.start()
    try:
        revision = watcher_module.ObservedRevision("unreadable", error_category="PermissionError")
        monkeypatch.setattr(watcher_module, "read_revisions", lambda paths: {file_path: revision})
        with caplog.at_level(logging.WARNING, logger="uvicorn.error.zerodock.reload"):
            assert await watcher.scan_once() == (file_path,)
            assert await watcher.scan_once() == ()
            revision = watcher_module.ObservedRevision(
                "unreadable", error_category="IsADirectoryError"
            )
            assert await watcher.scan_once() == (file_path,)
            assert await watcher.scan_once() == ()
        assert len(caplog.records) == 2
        assert "PermissionError" in caplog.text
        assert "IsADirectoryError" in caplog.text
    finally:
        await watcher.stop()


@pytest.mark.asyncio
@pytest.mark.parametrize("failed_scan", [1, 2])
async def test_fatal_startup_scan_cleans_partial_ownership(
    handler_factory, watcher_module, monkeypatch, failed_scan
):
    file_path = handler_factory("value = 1\n")
    original = watcher_module.read_revisions
    calls = 0

    def fail_scan(paths):
        nonlocal calls
        calls += 1
        if calls == failed_scan:
            raise RuntimeError("startup scan failed")
        return original(paths)

    monkeypatch.setattr(watcher_module, "read_revisions", fail_scan)
    watcher = watcher_module.HandlerWatcher([file_path])
    with pytest.raises(RuntimeError, match="startup scan failed"):
        await watcher.start()
    assert watcher.task is None
    assert loader.handler_module_name(file_path) not in loader._module_states


@pytest.mark.asyncio
async def test_partial_owner_registration_failure_is_cleaned(
    handler_factory, watcher_module, monkeypatch
):
    first = handler_factory("value = 1\n", "first.py")
    second = handler_factory("value = 2\n", "second.py")
    original = watcher_module.watch_handler_cache

    @contextmanager
    def register(module_name):
        if module_name == loader.handler_module_name(second):
            raise RuntimeError("owner registration failed")
        with original(module_name):
            yield

    monkeypatch.setattr(watcher_module, "watch_handler_cache", register)
    watcher = watcher_module.HandlerWatcher([first, second])
    with pytest.raises(RuntimeError, match="owner registration failed"):
        await watcher.start()
    assert watcher.task is None
    assert all(
        loader.handler_module_name(path) not in loader._module_states for path in (first, second)
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("outcome", ["exception", "cancelled", "returned"])
async def test_unexpected_observer_termination_is_visible(
    handler_factory, watcher_module, monkeypatch, caplog, outcome
):
    file_path = handler_factory("value = 1\n")
    watcher = watcher_module.HandlerWatcher([file_path], interval=60)
    if outcome != "cancelled":

        async def finish():
            if outcome == "exception":
                raise RuntimeError("observer failed")

        monkeypatch.setattr(watcher, "_run", finish)
    with caplog.at_level(logging.ERROR, logger="uvicorn.error.zerodock.reload"):
        await watcher.start()
        try:
            if outcome == "cancelled":
                watcher.task.cancel()
            with suppress(asyncio.CancelledError, RuntimeError):
                await watcher.task
            await asyncio.sleep(0)
            assert "observer" in caplog.text.lower()
            assert "unexpected" in caplog.text.lower()
            assert len(caplog.records) == 1
        finally:
            with suppress(asyncio.CancelledError, RuntimeError):
                await watcher.stop()
    assert loader.handler_module_name(file_path) not in loader._module_states


@pytest.mark.asyncio
async def test_partial_write_then_valid_source_converges(handler_factory, watcher_module):
    file_path = handler_factory("def handler(event): return 'A'\n")
    watcher = watcher_module.HandlerWatcher([file_path], interval=60)
    await watcher.start()
    try:
        file_path.write_text("def handler(\n", encoding="utf-8")
        assert await watcher.scan_once() == (file_path,)
        with pytest.raises(loader.HandlerLoadError):
            loader.load_handler(file_path, "handler", reload=True)
        file_path.write_text("def handler(event): return 'B'\n", encoding="utf-8")
        assert await watcher.scan_once() == (file_path,)
        assert loader.load_handler(file_path, "handler", reload=True)({}) == "B"
    finally:
        await watcher.stop()


@pytest.mark.asyncio
async def test_recoverable_errors_wait_between_scans(
    handler_factory, watcher_module, monkeypatch, caplog
):
    file_path = handler_factory("value = 1\n")
    watcher = watcher_module.HandlerWatcher([file_path])
    permits = asyncio.Queue()
    waiting = asyncio.Event()
    scanned = asyncio.Event()
    calls = 0

    async def wait_for_poll():
        waiting.set()
        return await permits.get()

    def read(paths):
        nonlocal calls
        calls += 1
        return {
            file_path: watcher_module.ObservedRevision(
                "unreadable", error_category="PermissionError"
            )
        }

    original_scan = watcher.scan_once

    async def scan():
        result = await original_scan()
        scanned.set()
        return result

    monkeypatch.setattr(watcher, "_wait_for_poll", wait_for_poll)
    monkeypatch.setattr(watcher, "scan_once", scan)
    monkeypatch.setattr(watcher_module, "read_revisions", read)
    with caplog.at_level(logging.WARNING, logger="uvicorn.error.zerodock.reload"):
        await watcher.start()
        try:
            await asyncio.wait_for(waiting.wait(), timeout=2)
            assert calls == 2
            for expected in (3, 4):
                waiting.clear()
                scanned.clear()
                permits.put_nowait(True)
                await asyncio.wait_for(scanned.wait(), timeout=2)
                await asyncio.wait_for(waiting.wait(), timeout=2)
                assert calls == expected
            assert len(caplog.records) == 1
        finally:
            permits.put_nowait(False)
            await watcher.stop()


@pytest.mark.asyncio
async def test_poll_wait_uses_configured_interval(watcher_module, monkeypatch):
    watcher = watcher_module.HandlerWatcher([])
    timeouts = []

    async def timed_out(awaitable, *, timeout):
        awaitable.close()
        timeouts.append(timeout)
        raise asyncio.TimeoutError

    with monkeypatch.context() as patch:
        patch.setattr(asyncio, "wait_for", timed_out)
        assert await watcher._wait_for_poll() is True
    assert timeouts == [0.1]


def _gate_reader(watcher_module, scan_barrier, monkeypatch):
    original = watcher_module.read_revisions
    handles = []

    def read(paths):
        with paths[0].open("rb") as source:
            handles.append(source)
            scan_barrier.wait()
            return original(paths)

    monkeypatch.setattr(watcher_module, "read_revisions", read)
    return handles


@pytest.mark.asyncio
async def test_cancelled_stop_drains_scan_before_releasing_ownership(
    handler_factory, watcher_module, scan_barrier, monkeypatch
):
    file_path = handler_factory("def handler(event): return 'A'\n")
    module_name = loader.handler_module_name(file_path)
    watcher = watcher_module.HandlerWatcher([file_path], interval=60)
    await watcher.start()
    observer = watcher.task
    old_handler = loader.load_handler(file_path, "handler", reload=True)
    invalidations = []
    monkeypatch.setattr(watcher_module, "invalidate_handler_cache", invalidations.append)
    handles = _gate_reader(watcher_module, scan_barrier, monkeypatch)
    scan = asyncio.create_task(watcher.scan_once())
    stopping = None
    try:
        assert await asyncio.to_thread(scan_barrier.entered.wait, 5)
        file_path.write_text("def handler(event): return 'B'\n", encoding="utf-8")
        stopping = asyncio.create_task(watcher.stop())
        await observer
        await asyncio.sleep(0)
        stopping.cancel()
        await asyncio.sleep(0)
        stopping.cancel()
        await asyncio.sleep(0)
        assert not stopping.done()
        assert loader._module_states[module_name].watcher_owners == 1
        assert not handles[0].closed
        scan_barrier.release.set()
        assert await scan == ()
        with pytest.raises(asyncio.CancelledError):
            await stopping
        assert handles[0].closed
        assert not invalidations
        assert watcher.task is None
        assert module_name not in loader._module_states
        assert old_handler({}) == "A"
        assert loader.load_handler(file_path, "handler", reload=True)({}) == "B"
    finally:
        scan_barrier.release.set()
        await asyncio.gather(
            scan, *([stopping] if stopping is not None else []), return_exceptions=True
        )
        with suppress(asyncio.CancelledError, RuntimeError):
            await watcher.stop()


@pytest.mark.asyncio
async def test_cancelled_scan_keeps_its_worker_until_the_file_is_closed(
    handler_factory, watcher_module, scan_barrier, monkeypatch
):
    file_path = handler_factory("value = 1\n")
    watcher = watcher_module.HandlerWatcher([file_path], interval=60)
    await watcher.start()
    handles = _gate_reader(watcher_module, scan_barrier, monkeypatch)
    scan = asyncio.create_task(watcher.scan_once())
    try:
        assert await asyncio.to_thread(scan_barrier.entered.wait, 5)
        scan.cancel()
        await asyncio.sleep(0)
        scan.cancel()
        await asyncio.sleep(0)
        assert not scan.done()
        assert not handles[0].closed
        scan_barrier.release.set()
        with pytest.raises(asyncio.CancelledError):
            await scan
        assert handles[0].closed
    finally:
        scan_barrier.release.set()
        await asyncio.gather(scan, return_exceptions=True)
        await watcher.stop()


@pytest.mark.asyncio
async def test_cancelled_startup_drains_its_initial_read(
    handler_factory, watcher_module, scan_barrier, monkeypatch
):
    file_path = handler_factory("value = 1\n")
    watcher = watcher_module.HandlerWatcher([file_path])
    handles = _gate_reader(watcher_module, scan_barrier, monkeypatch)
    starting = asyncio.create_task(watcher.start())
    try:
        assert await asyncio.to_thread(scan_barrier.entered.wait, 5)
        starting.cancel()
        await asyncio.sleep(0)
        starting.cancel()
        await asyncio.sleep(0)
        assert not starting.done()
        assert not handles[0].closed
        scan_barrier.release.set()
        with pytest.raises(asyncio.CancelledError):
            await starting
        assert handles[0].closed
        assert watcher.task is None
        assert loader.handler_module_name(file_path) not in loader._module_states
    finally:
        scan_barrier.release.set()
        await asyncio.gather(starting, return_exceptions=True)
        await watcher.stop()


@pytest.mark.asyncio
async def test_stop_during_startup_does_not_start_a_late_observer(
    handler_factory, watcher_module, scan_barrier, monkeypatch
):
    file_path = handler_factory("value = 1\n")
    watcher = watcher_module.HandlerWatcher([file_path])
    handles = _gate_reader(watcher_module, scan_barrier, monkeypatch)
    starting = asyncio.create_task(watcher.start())
    stopping = None
    try:
        assert await asyncio.to_thread(scan_barrier.entered.wait, 5)
        stopping = asyncio.create_task(watcher.stop())
        await asyncio.sleep(0)
        assert not stopping.done()
        assert not handles[0].closed
        scan_barrier.release.set()
        results = await asyncio.gather(starting, stopping, return_exceptions=True)
        assert isinstance(results[0], RuntimeError)
        assert "stopped during startup" in str(results[0])
        assert results[1] is None
        assert watcher.task is None
        assert loader.handler_module_name(file_path) not in loader._module_states
    finally:
        scan_barrier.release.set()
        await asyncio.gather(
            starting, *([stopping] if stopping is not None else []), return_exceptions=True
        )
        await watcher.stop()


@pytest.mark.asyncio
async def test_overlapping_starts_cannot_duplicate_observer_owners(
    handler_factory, watcher_module, scan_barrier, monkeypatch
):
    file_path = handler_factory("value = 1\n")
    watcher = watcher_module.HandlerWatcher([file_path], interval=60)
    existing_tasks = set(asyncio.all_tasks())
    _gate_reader(watcher_module, scan_barrier, monkeypatch)
    first = asyncio.create_task(watcher.start())
    second = None
    try:
        assert await asyncio.to_thread(scan_barrier.entered.wait, 5)
        second = asyncio.create_task(watcher.start())
        await asyncio.sleep(0)
        scan_barrier.release.set()
        await first
        with pytest.raises(RuntimeError, match="already running"):
            await second
        assert loader._module_states[loader.handler_module_name(file_path)].watcher_owners == 1
    finally:
        scan_barrier.release.set()
        await asyncio.gather(
            first, *([second] if second is not None else []), return_exceptions=True
        )
        await watcher.stop()
        extra = [
            task
            for task in asyncio.all_tasks()
            if task not in existing_tasks and task.get_name() == "zerodock-handler-reload"
        ]
        for task in extra:
            task.cancel()
        await asyncio.gather(*extra, return_exceptions=True)


@pytest.mark.asyncio
@pytest.mark.parametrize("outcome", ["exception", "cancelled"])
async def test_stop_consumes_an_already_reported_observer_failure(
    handler_factory, watcher_module, monkeypatch, caplog, outcome
):
    file_path = handler_factory("value = 1\n")
    watcher = watcher_module.HandlerWatcher([file_path], interval=60)
    if outcome == "exception":

        async def fail():
            raise RuntimeError("terminal observer failure")

        monkeypatch.setattr(watcher, "_run", fail)
    with caplog.at_level(logging.ERROR, logger="uvicorn.error.zerodock.reload"):
        await watcher.start()
        if outcome == "cancelled":
            watcher.task.cancel()
        with suppress(asyncio.CancelledError, RuntimeError):
            await watcher.task
        await asyncio.sleep(0)
        try:
            await watcher.stop()
        finally:
            assert loader.handler_module_name(file_path) not in loader._module_states
    assert len(caplog.records) == 1


@pytest.mark.asyncio
async def test_failed_observer_does_not_skip_draining_an_external_scan(
    handler_factory, watcher_module, scan_barrier, monkeypatch
):
    file_path = handler_factory("value = 1\n")
    watcher = watcher_module.HandlerWatcher([file_path])
    fail_now = asyncio.Event()

    async def fail():
        await fail_now.wait()
        raise RuntimeError("background observer failed")

    monkeypatch.setattr(watcher, "_run", fail)
    await watcher.start()
    observer = watcher.task
    handles = _gate_reader(watcher_module, scan_barrier, monkeypatch)
    scan = asyncio.create_task(watcher.scan_once())
    stopping = None
    try:
        assert await asyncio.to_thread(scan_barrier.entered.wait, 5)
        fail_now.set()
        with pytest.raises(RuntimeError, match="background observer failed"):
            await observer
        stopping = asyncio.create_task(watcher.stop())
        await asyncio.sleep(0)
        assert not stopping.done()
        assert not handles[0].closed
        assert loader._module_states[loader.handler_module_name(file_path)].watcher_owners == 1
        scan_barrier.release.set()
        await asyncio.gather(scan, stopping)
        assert handles[0].closed
    finally:
        scan_barrier.release.set()
        await asyncio.gather(
            scan, *([stopping] if stopping is not None else []), return_exceptions=True
        )
        with suppress(RuntimeError):
            await watcher.stop()


@pytest.mark.asyncio
async def test_stop_wakes_polling_and_leaves_shared_executor_usable(
    handler_factory, watcher_module, monkeypatch
):
    file_path = handler_factory("value = 1\n")
    watcher = watcher_module.HandlerWatcher([file_path], interval=60)
    waiting = asyncio.Event()
    original_wait = watcher._wait_for_poll
    shutdown_calls = []

    async def wait():
        waiting.set()
        return await original_wait()

    async def shutdown(*args, **kwargs):
        shutdown_calls.append(True)

    monkeypatch.setattr(watcher, "_wait_for_poll", wait)
    with monkeypatch.context() as patch:
        patch.setattr(asyncio.get_running_loop(), "shutdown_default_executor", shutdown)
        await watcher.start()
        try:
            await asyncio.wait_for(waiting.wait(), timeout=2)
            await asyncio.wait_for(watcher.stop(), timeout=2)
            assert not shutdown_calls
            executor_result = await asyncio.to_thread(lambda: "executor remains usable")
            assert executor_result == "executor remains usable"
        finally:
            await watcher.stop()


@pytest.mark.asyncio
async def test_repeated_observer_start_stop_releases_ownership(handler_factory, watcher_module):
    file_path = handler_factory("value = 1\n")
    watcher = watcher_module.HandlerWatcher([file_path], interval=60)
    for iteration in range(3):
        await watcher.start()
        assert loader._module_states[loader.handler_module_name(file_path)].watcher_owners == 1
        await asyncio.gather(watcher.stop(), watcher.stop())
        assert watcher.task is None
        assert loader.handler_module_name(file_path) not in loader._module_states
