"""Dynamic module loader and function invoker for serverless handlers."""

import hashlib
import importlib.util
import inspect
import linecache
import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock, RLock
from types import ModuleType
from typing import Any, Callable, cast
from weakref import WeakValueDictionary


class HandlerLoadError(Exception):
    """Raised when a handler file cannot be imported or callable not found."""

    pass


@dataclass
class _ModuleState:
    lock: RLock = field(default_factory=RLock)
    active_leases: int = 0
    watcher_owners: int = 0


_registry_lock = Lock()
_module_states: dict[str, _ModuleState] = {}
_owned_modules: WeakValueDictionary[str, ModuleType] = WeakValueDictionary()


def handler_module_name(file_path: Path) -> str:
    """Return the existing isolated module identity for a canonical handler path."""
    resolved_path = Path(file_path).resolve()
    return _resolved_module_name(resolved_path)


def _resolved_module_name(resolved_path: Path) -> str:
    path_hash = hashlib.sha256(str(resolved_path).encode("utf-8")).hexdigest()[:12]
    return f"zerodock.handlers.mod_{path_hash}"


def _retire_state(module_name: str, state: _ModuleState) -> None:
    if (
        state.active_leases == 0
        and state.watcher_owners == 0
        and _module_states.get(module_name) is state
    ):
        del _module_states[module_name]


@contextmanager
def _module_lease(module_name: str) -> Iterator[_ModuleState]:
    with _registry_lock:
        state = _module_states.get(module_name)
        if state is None:
            state = _ModuleState()
            _module_states[module_name] = state
        state.active_leases += 1
    try:
        with state.lock:
            yield state
    finally:
        with _registry_lock:
            state.active_leases -= 1
            _retire_state(module_name, state)


@contextmanager
def watch_handler_cache(module_name: str) -> Iterator[None]:
    """Pin shared coordination state for one observer's registration lifetime."""
    with _registry_lock:
        state = _module_states.get(module_name)
        if state is None:
            state = _ModuleState()
            _module_states[module_name] = state
        state.watcher_owners += 1
    try:
        yield
    finally:
        with _registry_lock:
            state.watcher_owners -= 1
            _retire_state(module_name, state)


def _discard_owned_module(module_name: str, expected: ModuleType | None = None) -> None:
    with _registry_lock:
        owned = _owned_modules.get(module_name)
        if owned is None or (expected is not None and owned is not expected):
            return
        if sys.modules.get(module_name) is owned:
            del sys.modules[module_name]
        del _owned_modules[module_name]


def invalidate_handler_cache(module_name: str) -> None:
    """Remove only a loader-owned module, leaving existing callables usable.

    Missing and foreign modules are ignored. This does not invalidate imported
    dependencies or guarantee freshness of timestamp-based bytecode by itself.
    """
    with _module_lease(module_name):
        _discard_owned_module(module_name)


def load_handler(file_path: Path, handler_name: str, *, reload: bool = False) -> Callable[..., Any]:
    """Dynamically loads a Python file and returns the target handler function.

    Uses an isolated module namespace in sys.modules to prevent collisions across handlers.

    Args:
        file_path: Absolute or relative Path to target Python file.
        handler_name: Name of the entrypoint callable function.
        reload: Execute fresh source bytes instead of consulting compiled bytecode.

    Returns:
        The callable handler object.

    Raises:
        HandlerLoadError: If file does not exist, syntax fails, or handler missing.
    """
    resolved_path = Path(file_path).resolve()

    module_name = _resolved_module_name(resolved_path)

    with _module_lease(module_name):
        with _registry_lock:
            previous = _owned_modules.get(module_name)
        module = None
        try:
            if not resolved_path.exists():
                raise HandlerLoadError(f"File not found: {resolved_path}")

            try:
                spec = importlib.util.spec_from_file_location(module_name, resolved_path)
                if spec is None or spec.loader is None:
                    raise HandlerLoadError(f"Could not load importlib spec for {resolved_path}")

                module = importlib.util.module_from_spec(spec)
                with _registry_lock:
                    sys.modules[module_name] = module
                    _owned_modules[module_name] = module
                if reload:
                    source = resolved_path.read_bytes()
                    code = compile(source, str(resolved_path), "exec", dont_inherit=True)
                    linecache.cache.pop(str(resolved_path), None)
                    linecache.cache.pop(os.path.normcase(str(resolved_path)), None)
                    exec(code, module.__dict__)
                else:
                    spec.loader.exec_module(module)
            except Exception as exc:
                raise HandlerLoadError(
                    f"Failed to load module from {resolved_path}: {exc}"
                ) from exc

            if not hasattr(module, handler_name):
                raise HandlerLoadError(
                    f"Handler function '{handler_name}' not found in module {resolved_path}"
                )

            handler_fn = getattr(module, handler_name)
            if not callable(handler_fn):
                raise HandlerLoadError(
                    f"Target attribute '{handler_name}' in {resolved_path} is not callable."
                )

            return cast(Callable[..., Any], handler_fn)
        except BaseException:
            failed_module = module if module is not None else previous
            if failed_module is not None:
                _discard_owned_module(module_name, expected=failed_module)
            raise


def invoke_handler(handler_fn: Callable[..., Any], event: dict, context: Any = None) -> Any:
    """Executes a handler function, handling sync/async and parameter arity.

    Args:
        handler_fn: Target callable function.
        event: Invocation event dictionary.
        context: Optional InvocationContext runtime object.

    Returns:
        The handler return value, or a coroutine if async.
    """
    # Inspect callable signature to see if it accepts 1 or 2+ parameters
    sig = inspect.signature(handler_fn)
    params = list(sig.parameters.values())

    # Check if only accepting event (1 positional arg or kwargs)
    if len(params) == 1:
        result = handler_fn(event)
    else:
        result = handler_fn(event, context)

    # If the handler is a coroutine or returned a coroutine, return the coroutine
    if inspect.iscoroutine(result):
        return result

    return result
