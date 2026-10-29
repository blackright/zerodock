"""Unit tests for ZeroDock dynamic module loader."""

import hashlib
import importlib.machinery
import io
import linecache
import os
import pdb
import py_compile
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from pathlib import Path
from threading import Event
from types import ModuleType

import pytest

from zerodock.config.parser import load_config
from zerodock.engine import loader
from zerodock.engine.context import InvocationContext
from zerodock.engine.loader import HandlerLoadError, invoke_handler, load_handler


def test_load_and_invoke_sync_handler(track_handler):
    """Verify loading and invoking standard two-argument sync handler."""
    handler_file = Path("tests/fixtures/handlers/hello.py").resolve()
    track_handler(handler_file)
    handler_fn = load_handler(handler_file, "lambda_handler")

    event = {"queryStringParameters": {"name": "Alice"}}
    context = InvocationContext(function_name="hello")

    result = invoke_handler(handler_fn, event, context)
    assert result["statusCode"] == 200
    assert result["body"]["message"] == "Hello, Alice!"
    assert result["body"]["requestId"] == context.request_id


def test_load_handler_missing_file():
    """Verify HandlerLoadError when source file does not exist."""
    missing_file = Path("tests/fixtures/handlers/not_found.py").resolve()
    with pytest.raises(HandlerLoadError, match="File not found"):
        load_handler(missing_file, "handler")


def test_load_handler_missing_function(track_handler):
    """Verify HandlerLoadError when function name does not exist in module."""
    handler_file = Path("tests/fixtures/handlers/hello.py").resolve()
    track_handler(handler_file)
    with pytest.raises(HandlerLoadError, match="not found in module"):
        load_handler(handler_file, "non_existent_function")


def test_load_handler_not_callable(handler_factory):
    """Verify HandlerLoadError when attribute is not a callable function."""
    var_file = handler_factory("my_var = 42\n", "constant.py")

    with pytest.raises(HandlerLoadError, match="is not callable"):
        load_handler(var_file, "my_var")


@pytest.mark.asyncio
async def test_invoke_async_handler(handler_factory):
    """Verify invoking coroutine async handler works seamlessly."""
    async_file = handler_factory(
        "async def async_handler(event, context):\n"
        "    return {'statusCode': 200, 'body': 'async result'}\n",
        "async_fn.py",
    )
    handler_fn = load_handler(async_file, "async_handler")
    result = await invoke_handler(handler_fn, {}, None)
    assert result["body"] == "async result"


def test_invoke_single_arg_handler(handler_factory):
    """Verify handler expecting only 'event' parameter is called without error."""
    single_arg_file = handler_factory(
        "def single_handler(event):\n"
        "    return {'statusCode': 200, 'received': event.get('action')}\n",
        "single_arg.py",
    )
    handler_fn = load_handler(single_arg_file, "single_handler")
    result = invoke_handler(handler_fn, {"action": "ping"}, None)
    assert result["received"] == "ping"


def test_handler_module_name_preserves_existing_algorithm(handler_factory):
    file_path = handler_factory("def handler(event): return 'ok'\n")
    expected = hashlib.sha256(str(file_path.resolve()).encode("utf-8")).hexdigest()[:12]
    assert loader.handler_module_name(file_path) == f"zerodock.handlers.mod_{expected}"


def test_handler_module_name_normalizes_relative_path(handler_factory, monkeypatch):
    file_path = handler_factory("def handler(event): return 'ok'\n")
    monkeypatch.chdir(file_path.parent)
    assert loader.handler_module_name(Path(file_path.name)) == loader.handler_module_name(file_path)


@pytest.mark.parametrize("reload", [False, True])
@pytest.mark.parametrize("missing", [False, True])
def test_load_handler_resolves_target_once(handler_factory, monkeypatch, reload, missing):
    file_path = handler_factory("def handler(event): return 'ok'\n")
    expected_name = loader.handler_module_name(file_path)
    if missing:
        file_path.unlink()
    monkeypatch.chdir(file_path.parent)
    original_resolve = Path.resolve
    resolutions = []

    def record_resolve(path, *args, **kwargs):
        resolutions.append(path)
        return original_resolve(path, *args, **kwargs)

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "resolve", record_resolve)
        if missing:
            with pytest.raises(HandlerLoadError, match="File not found"):
                load_handler(Path(file_path.name), "handler", reload=reload)
        else:
            handler = load_handler(Path(file_path.name), "handler", reload=reload)
            assert handler({}) == "ok"
            assert handler.__module__ == expected_name
        assert resolutions == [Path(file_path.name)]


def test_public_module_identity_still_resolves_input(handler_factory, monkeypatch):
    file_path = handler_factory("def handler(event): return 'ok'\n")
    expected = loader.handler_module_name(file_path)
    monkeypatch.chdir(file_path.parent)
    original_resolve = Path.resolve
    resolutions = []

    def record_resolve(path, *args, **kwargs):
        resolutions.append(path)
        return original_resolve(path, *args, **kwargs)

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "resolve", record_resolve)
        assert loader.handler_module_name(Path(file_path.name)) == expected
        assert resolutions == [Path(file_path.name)]


def test_same_basename_handlers_remain_isolated(handler_factory):
    first = handler_factory("def handler(event): return 'first'\n", "first/handler.py")
    second = handler_factory("def handler(event): return 'second'\n", "second/handler.py")
    first_fn = load_handler(first, "handler")
    second_fn = load_handler(second, "handler")
    assert loader.handler_module_name(first) != loader.handler_module_name(second)
    loader.invalidate_handler_cache(loader.handler_module_name(first))
    assert invoke_handler(first_fn, {}) == "first"
    assert invoke_handler(second_fn, {}) == "second"
    assert loader.handler_module_name(second) in sys.modules


def test_invalidation_is_idempotent_for_absent_modules():
    module_name = "zerodock.handlers.mod_phase2_absent"
    loader.invalidate_handler_cache(module_name)
    loader.invalidate_handler_cache(module_name)
    assert module_name not in loader._module_states


def test_invalidation_removes_only_owned_module(handler_factory):
    file_path = handler_factory("def handler(event): return 'ok'\n")
    handler = load_handler(file_path, "handler")
    module_name = loader.handler_module_name(file_path)
    assert sys.modules[module_name].handler is handler
    loader.invalidate_handler_cache(module_name)
    assert module_name not in sys.modules
    assert module_name not in loader._owned_modules
    assert handler({}) == "ok"


@pytest.mark.parametrize("module_name", ["json", "zerodock.handlers.mod_foreign"])
def test_invalidation_preserves_foreign_modules(module_name, monkeypatch):
    foreign = ModuleType(module_name)
    monkeypatch.setitem(sys.modules, module_name, foreign)
    loader.invalidate_handler_cache(module_name)
    assert sys.modules[module_name] is foreign


def test_invalidation_preserves_replaced_module(handler_factory, monkeypatch):
    file_path = handler_factory("def handler(event): return 'ok'\n")
    load_handler(file_path, "handler")
    module_name = loader.handler_module_name(file_path)
    owned = sys.modules[module_name]
    foreign = ModuleType(module_name)
    with monkeypatch.context() as replacement:
        replacement.setitem(sys.modules, module_name, foreign)
        loader.invalidate_handler_cache(module_name)
        assert sys.modules[module_name] is foreign
    assert sys.modules[module_name] is owned


@pytest.mark.parametrize("reload_enabled", [False, True])
@pytest.mark.parametrize(
    ("source", "handler_name", "message"),
    [
        ("raise RuntimeError('broken import')\n", "handler", "Failed to load module"),
        ("def broken syntax\n", "handler", "Failed to load module"),
        ("value = 1\n", "handler", "not found in module"),
        ("handler = 1\n", "handler", "is not callable"),
    ],
)
def test_failed_load_removes_owned_registration(
    handler_factory, source, handler_name, message, reload_enabled
):
    valid_source = "def handler(event): return 'A'\n"
    file_path = handler_factory(valid_source)
    assert load_handler(file_path, "handler", reload=reload_enabled)({}) == "A"
    file_path.write_text(source, encoding="utf-8")
    with pytest.raises(HandlerLoadError, match=message):
        load_handler(file_path, handler_name, reload=reload_enabled)
    module_name = loader.handler_module_name(file_path)
    assert module_name not in sys.modules
    assert module_name not in loader._owned_modules
    assert module_name not in loader._module_states
    file_path.write_text(valid_source.replace("'A'", "'B'"), encoding="utf-8")
    changed = file_path.stat()
    os.utime(file_path, ns=(changed.st_atime_ns, changed.st_mtime_ns + 2_000_000_000))
    assert load_handler(file_path, "handler", reload=reload_enabled)({}) == "B"


@pytest.mark.parametrize("reload_enabled", [False, True])
def test_failed_load_does_not_remove_newer_registration(
    handler_factory, monkeypatch, reload_enabled
):
    bridge = ModuleType("phase2_replacement_bridge")
    replacement = ModuleType("replacement")
    bridge.replacement = replacement
    monkeypatch.setitem(sys.modules, bridge.__name__, bridge)
    file_path = handler_factory(
        "import sys\n"
        "from phase2_replacement_bridge import replacement\n"
        "sys.modules[__name__] = replacement\n"
        "raise RuntimeError('failure after replacement')\n"
    )
    module_name = loader.handler_module_name(file_path)
    try:
        with pytest.raises(HandlerLoadError):
            load_handler(file_path, "handler", reload=reload_enabled)
        assert sys.modules[module_name] is replacement
    finally:
        if sys.modules.get(module_name) is replacement:
            sys.modules.pop(module_name)


def test_successful_calls_execute_a_new_module_each_time(handler_factory):
    file_path = handler_factory(
        "counter = globals().get('counter', 0) + 1\ndef handler(event): return counter\n"
    )
    first = load_handler(file_path, "handler")
    second = load_handler(file_path, "handler")
    assert first is not second
    assert invoke_handler(first, {}) == invoke_handler(second, {}) == 1


def test_temporary_config_factory_uses_existing_parser(handler_factory, config_factory):
    file_path = handler_factory("def handler(event): return 'ok'\n")
    config = load_config(config_factory(file_path))
    assert config.routes["/test"].file.resolve() == file_path


def test_handler_factory_cannot_escape_temporary_directory(handler_factory):
    with pytest.raises(ValueError, match="temporary directory"):
        handler_factory("value = 1\n", "../outside.py")


def test_leases_are_reentrant_and_retire_when_unused(handler_factory):
    file_path = handler_factory("def handler(event): return 'ok'\n")
    module_name = loader.handler_module_name(file_path)
    with loader._module_lease(module_name) as outer:
        assert outer.active_leases == 1
        with loader._module_lease(module_name) as inner:
            assert inner is outer
            assert inner.active_leases == 2
            load_handler(file_path, "handler")
            loader.invalidate_handler_cache(module_name)
        assert outer.active_leases == 1
    assert module_name not in loader._module_states


def test_lease_exception_releases_registry_entry(handler_factory):
    module_name = loader.handler_module_name(handler_factory("value = 1\n"))
    with pytest.raises(RuntimeError):
        with loader._module_lease(module_name):
            raise RuntimeError("test error")
    assert module_name not in loader._module_states


def test_two_watcher_owners_preserve_shared_state(handler_factory):
    file_path = handler_factory("def handler(event): return 'ok'\n")
    module_name = loader.handler_module_name(file_path)
    with loader.watch_handler_cache(module_name):
        state = loader._module_states[module_name]
        assert state.watcher_owners == 1
        with loader.watch_handler_cache(module_name):
            assert state.watcher_owners == 2
            handler = load_handler(file_path, "handler")
        assert state.watcher_owners == 1
        assert loader._module_states[module_name] is state
        assert sys.modules[module_name].handler is handler
    assert module_name not in loader._module_states
    assert sys.modules[module_name].handler is handler
    assert invoke_handler(load_handler(file_path, "handler"), {}) == "ok"


def test_watcher_owner_exception_releases_registration(handler_factory):
    module_name = loader.handler_module_name(handler_factory("value = 1\n"))
    with pytest.raises(RuntimeError):
        with loader.watch_handler_cache(module_name):
            raise RuntimeError("test error")
    assert module_name not in loader._module_states


def test_waiting_lease_pins_state_after_watcher_shutdown(handler_factory, monkeypatch):
    module_name = loader.handler_module_name(handler_factory("value = 1\n"))
    waiting = Event()

    def acquire_state():
        with loader._module_lease(module_name) as acquired:
            return acquired

    with ThreadPoolExecutor(max_workers=1) as workers:
        with ExitStack() as owners:
            owners.enter_context(loader.watch_handler_cache(module_name))
            with loader._module_lease(module_name) as state:
                original_lock = state.lock

                class SignalledLock:
                    def __enter__(self):
                        waiting.set()
                        return original_lock.__enter__()

                    def __exit__(self, *exception):
                        return original_lock.__exit__(*exception)

                with monkeypatch.context() as patch:
                    patch.setattr(state, "lock", SignalledLock())
                    pending = workers.submit(acquire_state)
                    assert waiting.wait(timeout=5)
                    assert state.active_leases == 2
                owners.close()
                assert state.watcher_owners == 0
                assert loader._module_states[module_name] is state
            assert pending.result(timeout=5) is state
            assert state.active_leases == 0
        assert module_name not in loader._module_states


def test_unrelated_module_can_load_while_another_is_locked(handler_factory):
    first = handler_factory("value = 1\n", "first.py")
    second = handler_factory("def handler(event): return 'ok'\n", "second.py")
    with ThreadPoolExecutor(max_workers=1) as workers:
        with loader._module_lease(loader.handler_module_name(first)):
            pending = workers.submit(load_handler, second, "handler")
            assert invoke_handler(pending.result(timeout=5), {}) == "ok"


@pytest.mark.parametrize("reload_enabled", [False, True])
@pytest.mark.parametrize("fail_import", [False, True])
def test_invalidation_waits_for_module_initialization(
    handler_factory, scan_barrier, monkeypatch, reload_enabled, fail_import
):
    bridge = ModuleType("phase2_loading_bridge")

    def wait():
        scan_barrier.wait()
        if fail_import:
            raise RuntimeError("gated import failed")

    bridge.wait = wait
    monkeypatch.setitem(sys.modules, bridge.__name__, bridge)
    file_path = handler_factory(
        "from phase2_loading_bridge import wait\nwait()\ndef handler(event): return 'ready'\n"
    )
    module_name = loader.handler_module_name(file_path)
    with ThreadPoolExecutor(max_workers=2) as workers:
        pending_load = workers.submit(load_handler, file_path, "handler", reload=reload_enabled)
        try:
            assert scan_barrier.entered.wait(timeout=5)
            state = loader._module_states[module_name]
            attempted = Event()
            original_lock = state.lock

            class SignalledLock:
                def __enter__(self):
                    attempted.set()
                    return original_lock.__enter__()

                def __exit__(self, *exception):
                    return original_lock.__exit__(*exception)

            with monkeypatch.context() as patch:
                patch.setattr(state, "lock", SignalledLock())
                pending_invalidate = workers.submit(loader.invalidate_handler_cache, module_name)
                assert attempted.wait(timeout=5)
                assert not pending_invalidate.done()
                assert state.active_leases == 2
                scan_barrier.release.set()
                if fail_import:
                    with pytest.raises(HandlerLoadError, match="gated import failed"):
                        pending_load.result(timeout=5)
                else:
                    assert invoke_handler(pending_load.result(timeout=5), {}) == "ready"
                pending_invalidate.result(timeout=5)
        finally:
            scan_barrier.release.set()
    assert module_name not in sys.modules
    assert module_name not in loader._module_states


def test_module_lock_is_not_held_during_invocation(handler_factory, scan_barrier, monkeypatch):
    bridge = ModuleType("phase2_invocation_bridge")
    bridge.wait = scan_barrier.wait
    monkeypatch.setitem(sys.modules, bridge.__name__, bridge)
    file_path = handler_factory(
        "from phase2_invocation_bridge import wait\n"
        "def handler(event):\n"
        "    wait()\n"
        "    return 'finished'\n"
    )
    handler = load_handler(file_path, "handler")
    module_name = loader.handler_module_name(file_path)
    with ThreadPoolExecutor(max_workers=2) as workers:
        pending = workers.submit(invoke_handler, handler, {})
        try:
            assert scan_barrier.entered.wait(timeout=5)
            invalidation = workers.submit(loader.invalidate_handler_cache, module_name)
            invalidation.result(timeout=5)
            assert module_name not in sys.modules
        finally:
            scan_barrier.release.set()
        assert pending.result(timeout=5) == "finished"


def test_reload_bypasses_same_timestamp_bytecode(handler_factory):
    file_path = handler_factory("def handler(event): return 'A'\n")
    bytecode = Path(py_compile.compile(str(file_path), doraise=True))
    original_bytecode = bytecode.read_bytes()
    original_stat = file_path.stat()
    assert invoke_handler(load_handler(file_path, "handler"), {}) == "A"
    file_path.write_text("def handler(event): return 'B'\n", encoding="utf-8")
    os.utime(file_path, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
    loader.invalidate_handler_cache(loader.handler_module_name(file_path))
    assert invoke_handler(load_handler(file_path, "handler", reload=True), {}) == "B"
    assert bytecode.read_bytes() == original_bytecode


@pytest.mark.parametrize("encoding", ["utf-8-sig", "latin-1"])
def test_reload_respects_python_source_encoding(handler_factory, encoding):
    file_path = handler_factory("value = None\n")
    source = f"# coding: {encoding}\ndef handler(event): return 'caf\u00e9'\n"
    file_path.write_bytes(source.encode(encoding))
    assert invoke_handler(load_handler(file_path, "handler", reload=True), {}) == "caf\u00e9"


def test_reload_preserves_module_metadata_and_source_filename(handler_factory):
    file_path = handler_factory(
        "from __future__ import annotations\n"
        "def handler(event: int): return __name__, __file__, __spec__.origin\n"
    )
    handler = load_handler(file_path, "handler", reload=True)
    assert handler.__annotations__["event"] == "int"
    assert handler.__code__.co_filename == str(file_path)
    assert handler(0) == (loader.handler_module_name(file_path), str(file_path), str(file_path))


def test_reload_compiles_bytes_without_inheriting_flags(handler_factory, monkeypatch):
    file_path = handler_factory("def handler(event): return 'ok'\n")
    calls = []

    def compile_source(source, filename, mode, **kwargs):
        calls.append((source, filename, mode, kwargs))
        return compile(source, filename, mode, **kwargs)

    monkeypatch.setattr(loader, "compile", compile_source, raising=False)
    load_handler(file_path, "handler", reload=True)
    assert calls == [(file_path.read_bytes(), str(file_path), "exec", {"dont_inherit": True})]


@pytest.mark.parametrize("reload_enabled", [False, True])
def test_reload_does_not_cache_callable_or_globals(handler_factory, reload_enabled):
    file_path = handler_factory(
        "counter = globals().get('counter', 0) + 1\ndef handler(event): return counter\n"
    )
    first = load_handler(file_path, "handler", reload=reload_enabled)
    second = load_handler(file_path, "handler", reload=reload_enabled)
    assert first is not second
    assert first({}) == second({}) == 1


def test_reload_supports_multiple_entrypoints(handler_factory):
    file_path = handler_factory("def first(event): return 'one'\ndef second(event): return 'two'\n")
    assert load_handler(file_path, "first", reload=True)({}) == "one"
    assert load_handler(file_path, "second", reload=True)({}) == "two"


def test_reload_is_keyword_only(handler_factory):
    file_path = handler_factory("def handler(event): return 'ok'\n")
    with pytest.raises(TypeError):
        load_handler(file_path, "handler", True)


def test_reload_traceback_points_to_original_source(handler_factory):
    file_path = handler_factory("def handler(event):\n    raise ValueError('test failure')\n")
    handler = load_handler(file_path, "handler", reload=True)
    with pytest.raises(ValueError) as error:
        handler({})
    frame = traceback.extract_tb(error.value.__traceback__)[-1]
    assert frame.filename == str(file_path)
    assert frame.lineno == 2
    assert frame.name == "handler"


@pytest.mark.parametrize("reload_enabled", [False, True])
def test_missing_source_removes_previously_owned_module(handler_factory, reload_enabled):
    file_path = handler_factory("def handler(event): return 'old'\n")
    old_handler = load_handler(file_path, "handler", reload=reload_enabled)
    module_name = loader.handler_module_name(file_path)
    file_path.unlink()
    with pytest.raises(HandlerLoadError, match="File not found"):
        load_handler(file_path, "handler", reload=reload_enabled)
    assert module_name not in sys.modules
    assert module_name not in loader._owned_modules
    assert module_name not in loader._module_states
    assert old_handler({}) == "old"
    file_path.write_text("def handler(event): return 'restored'\n", encoding="utf-8")
    assert load_handler(file_path, "handler", reload=reload_enabled)({}) == "restored"


@pytest.mark.parametrize("reload_enabled", [False, True])
def test_unreadable_source_fails_without_stale_fallback(
    handler_factory, monkeypatch, reload_enabled
):
    file_path = handler_factory("def handler(event): return 'old'\n")
    load_handler(file_path, "handler", reload=reload_enabled)
    original_read = Path.read_bytes
    original_get = importlib.machinery.SourceFileLoader.get_data

    def read_bytes(path):
        if path == file_path:
            raise PermissionError("test read denied")
        return original_read(path)

    def get_data(source_loader, filename):
        if Path(filename).is_relative_to(file_path.parent):
            raise PermissionError("test read denied")
        return original_get(source_loader, filename)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "read_bytes", read_bytes)
        patch.setattr(importlib.machinery.SourceFileLoader, "get_data", get_data)
        with pytest.raises(HandlerLoadError, match="test read denied"):
            load_handler(file_path, "handler", reload=reload_enabled)
    module_name = loader.handler_module_name(file_path)
    assert module_name not in sys.modules
    assert module_name not in loader._owned_modules
    assert load_handler(file_path, "handler", reload=reload_enabled)({}) == "old"


@pytest.mark.parametrize("reload_enabled", [False, True])
def test_failed_outer_load_preserves_newer_owned_registration(
    handler_factory, monkeypatch, reload_enabled
):
    bridge = ModuleType("phase4_nested_bridge")
    bridge.calls = 0
    bridge.load = load_handler
    bridge.reload_enabled = reload_enabled
    monkeypatch.setitem(sys.modules, bridge.__name__, bridge)
    file_path = handler_factory(
        "import phase4_nested_bridge as state\n"
        "def handler(event): return 'newer'\n"
        "state.calls += 1\n"
        "if state.calls == 1:\n"
        "    state.newer = state.load(__file__, 'handler', reload=state.reload_enabled)\n"
        "    raise RuntimeError('outer load failed')\n"
    )
    with pytest.raises(HandlerLoadError, match="outer load failed"):
        load_handler(file_path, "handler", reload=reload_enabled)
    module_name = loader.handler_module_name(file_path)
    assert sys.modules[module_name].handler is bridge.newer
    assert loader._owned_modules[module_name] is sys.modules[module_name]
    assert bridge.newer({}) == "newer"


@pytest.mark.parametrize("reload_enabled", [False, True])
def test_waiting_load_survives_failed_load_cleanup(
    handler_factory, scan_barrier, monkeypatch, reload_enabled
):
    bridge = ModuleType("phase4_waiting_bridge")
    calls = 0

    def enter():
        nonlocal calls
        calls += 1
        if calls == 1:
            scan_barrier.wait()
            raise RuntimeError("first load failed")

    bridge.enter = enter
    monkeypatch.setitem(sys.modules, bridge.__name__, bridge)
    file_path = handler_factory(
        "from phase4_waiting_bridge import enter\nenter()\ndef handler(event): return 'new'\n"
    )
    module_name = loader.handler_module_name(file_path)
    attempted = Event()
    with ThreadPoolExecutor(max_workers=2) as workers:
        first = workers.submit(load_handler, file_path, "handler", reload=reload_enabled)
        try:
            assert scan_barrier.entered.wait(timeout=5)
            state = loader._module_states[module_name]
            original_lock = state.lock

            class SignalledLock:
                def __enter__(self):
                    attempted.set()
                    return original_lock.__enter__()

                def __exit__(self, *exception):
                    return original_lock.__exit__(*exception)

            with monkeypatch.context() as patch:
                patch.setattr(state, "lock", SignalledLock())
                second = workers.submit(load_handler, file_path, "handler", reload=reload_enabled)
                assert attempted.wait(timeout=5)
                assert state.active_leases == 2
                assert not second.done()
                scan_barrier.release.set()
                with pytest.raises(HandlerLoadError, match="first load failed"):
                    first.result(timeout=5)
                handler = second.result(timeout=5)
            assert sys.modules[module_name].handler is handler
            assert handler({}) == "new"
        finally:
            scan_barrier.release.set()
    assert module_name not in loader._module_states


@pytest.mark.parametrize("reload_enabled", [False, True])
def test_native_breakpoint_accepts_debugger_commands(handler_factory, monkeypatch, reload_enabled):
    file_path = handler_factory("def handler(event):\n    breakpoint()\n    return event['name']\n")
    output = io.StringIO()
    debugger = pdb.Pdb(
        stdin=io.StringIO("p event['name']\ncontinue\n"), stdout=output, readrc=False
    )
    handler = load_handler(file_path, "handler", reload=reload_enabled)
    with monkeypatch.context() as patch:
        patch.setattr(sys, "breakpointhook", debugger.set_trace)
        assert invoke_handler(handler, {"name": "phase5-debug"}) == "phase5-debug"
    transcript = output.getvalue()
    assert str(file_path).lower() in transcript.lower()
    assert "'phase5-debug'" in transcript
    assert "(Pdb)" in transcript


def test_debugger_lists_fresh_source_after_same_metadata_save(handler_factory, monkeypatch):
    source = "def handler(event):\n    breakpoint()\n    return 'A'\n"
    file_path = handler_factory(source)
    original_stat = file_path.stat()
    try:
        for version in ("A", "B"):
            if version == "B":
                file_path.write_text(source.replace("'A'", "'B'"), encoding="utf-8")
                os.utime(file_path, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
                loader.invalidate_handler_cache(loader.handler_module_name(file_path))
            output = io.StringIO()
            debugger = pdb.Pdb(stdin=io.StringIO("list\ncontinue\n"), stdout=output, readrc=False)
            handler = load_handler(file_path, "handler", reload=True)
            with monkeypatch.context() as patch:
                patch.setattr(sys, "breakpointhook", debugger.set_trace)
                assert invoke_handler(handler, {}) == version
            assert f"return '{version}'" in output.getvalue()
    finally:
        linecache.cache.pop(str(file_path), None)
        linecache.cache.pop(os.path.normcase(str(file_path)), None)


def test_reload_source_cache_refresh_is_targeted(handler_factory, monkeypatch):
    file_path = handler_factory("def handler(event): return 'ok'\n")
    cached = (file_path.stat().st_size, file_path.stat().st_mtime, ["cached\n"], str(file_path))
    unrelated = str(file_path.parent / "unrelated.py")
    monkeypatch.setitem(linecache.cache, str(file_path), cached)
    monkeypatch.setitem(linecache.cache, os.path.normcase(str(file_path)), cached)
    monkeypatch.setitem(linecache.cache, unrelated, cached)
    load_handler(file_path, "handler")
    assert linecache.cache[str(file_path)] is cached
    load_handler(file_path, "handler", reload=True)
    assert str(file_path) not in linecache.cache
    assert os.path.normcase(str(file_path)) not in linecache.cache
    assert linecache.cache[unrelated] is cached
