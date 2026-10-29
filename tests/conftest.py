"""Isolated file factories and synchronization helpers for handler tests."""

import hashlib
import sys
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from threading import Event

import pytest
import yaml

from zerodock.engine import loader


@pytest.fixture
def track_handler(request: pytest.FixtureRequest) -> Callable[[Path], None]:
    tracked: set[str] = set()

    def track(file_path: Path) -> None:
        resolved = file_path.resolve()
        digest = hashlib.sha256(str(resolved).encode("utf-8")).hexdigest()[:12]
        module_name = f"zerodock.handlers.mod_{digest}"
        if module_name in tracked:
            return
        tracked.add(module_name)
        previous = sys.modules.get(module_name)

        def cleanup() -> None:
            current = sys.modules.get(module_name)
            if current is previous:
                return
            invalidate = getattr(loader, "invalidate_handler_cache", None)
            if invalidate is not None:
                invalidate(module_name)
            module_file = getattr(current, "__file__", None)
            if (
                sys.modules.get(module_name) is current
                and module_file is not None
                and Path(module_file).resolve() == resolved
            ):
                sys.modules.pop(module_name, None)
            if previous is not None and module_name not in sys.modules:
                sys.modules[module_name] = previous

        request.addfinalizer(cleanup)

    return track


@pytest.fixture
def handler_factory(tmp_path: Path, track_handler: Callable[[Path], None]) -> Callable[..., Path]:
    def create(source: str, relative_path: str = "handler.py") -> Path:
        file_path = (tmp_path / relative_path).resolve()
        if not file_path.is_relative_to(tmp_path.resolve()):
            raise ValueError("Handler fixtures must stay inside their temporary directory")
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(source, encoding="utf-8")
        track_handler(file_path)
        return file_path

    return create


@pytest.fixture
def config_factory(tmp_path: Path) -> Callable[..., Path]:
    def create(handler_path: Path, handler_name: str = "handler", route: str = "/test") -> Path:
        config_path = tmp_path / "serverless-local.yaml"
        config_path.write_text(
            yaml.safe_dump(
                {
                    "version": "1.0",
                    "routes": {route: {"file": str(handler_path), "handler": handler_name}},
                }
            ),
            encoding="utf-8",
        )
        return config_path

    return create


@dataclass
class ScanBarrier:
    entered: Event = field(default_factory=Event)
    release: Event = field(default_factory=Event)

    def wait(self) -> None:
        self.entered.set()
        if not self.release.wait(timeout=5):
            raise TimeoutError("Test did not release its worker barrier")


@pytest.fixture
def scan_barrier() -> Iterator[ScanBarrier]:
    barrier = ScanBarrier()
    try:
        yield barrier
    finally:
        barrier.release.set()
