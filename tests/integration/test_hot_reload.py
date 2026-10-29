"""Handler refresh through actual application lifespan and HTTP dispatch."""

import asyncio
import importlib
import json
import logging
import os
import py_compile
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from pathlib import Path
from types import ModuleType

import httpx
import pytest

from zerodock.config.models import RouteDefinition, ServerlessConfig
from zerodock.config.parser import ConfigurationError, load_config
from zerodock.engine import loader
from zerodock.gateway.app import create_app


@pytest.mark.asyncio
@pytest.mark.parametrize("prefix", ["", "async "])
async def test_http_response_refreshes_after_invalidation(handler_factory, config_factory, prefix):
    source = f"{prefix}def handler(event): return {{'statusCode': 200, 'body': 'A'}}\n"
    file_path = handler_factory(source)
    app = create_app(load_config(config_factory(file_path)), reload=True)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            assert (await client.get("/test")).text == "A"
            file_path.write_text(source.replace("'A'", "'B'"), encoding="utf-8")
            assert await app.state.handler_watcher.scan_once() == (file_path,)
            assert (await client.get("/test")).text == "B"


@pytest.fixture
def recovery_routes(handler_factory):
    source = "def handler(event): return {'statusCode': 200, 'body': 'A'}\n"
    file_path = handler_factory(source, "affected.py")
    healthy = handler_factory(
        "def handler(event): return {'statusCode': 200, 'body': 'healthy'}\n", "healthy.py"
    )
    config = ServerlessConfig(
        routes={
            "/affected": RouteDefinition(file=file_path),
            "/healthy": RouteDefinition(file=healthy),
        }
    )
    return file_path, source, config


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "broken_source",
    [
        "def handler(\n",
        "import zerodock_phase4_missing_dependency\n",
        "different_name = 1\n",
        "handler = 1\n",
    ],
)
async def test_error_response_and_corrected_save_recover(recovery_routes, broken_source):
    file_path, source, config = recovery_routes
    app = create_app(config, reload=True)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            assert (await client.get("/affected")).text == "A"
            file_path.write_text(broken_source, encoding="utf-8")
            await app.state.handler_watcher.scan_once()
            response = await client.get("/affected")
            assert response.status_code == 500
            error = response.json()
            assert set(error) == {"error", "exceptionType", "message", "requestId"}
            assert error["error"] == "InternalServerError"
            assert error["exceptionType"] == "HandlerLoadError"
            assert error["requestId"]
            assert loader.handler_module_name(file_path) not in sys.modules
            assert (await client.get("/healthy")).text == "healthy"
            file_path.write_text(source.replace("'A'", "'B'"), encoding="utf-8")
            await app.state.handler_watcher.scan_once()
            assert (await client.get("/affected")).text == "B"


@pytest.mark.asyncio
async def test_deleted_route_errors_and_recreation_recovers(recovery_routes):
    file_path, source, config = recovery_routes
    app = create_app(config, reload=True)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            assert (await client.get("/affected")).text == "A"
            file_path.unlink()
            assert await app.state.handler_watcher.scan_once() == (file_path,)
            assert (await client.get("/affected")).status_code == 500
            assert (await client.get("/healthy")).text == "healthy"
            file_path.write_text(source.replace("'A'", "'B'"), encoding="utf-8")
            await app.state.handler_watcher.scan_once()
            assert (await client.get("/affected")).text == "B"


@pytest.mark.asyncio
async def test_unreadable_route_errors_without_affecting_healthy_route(
    recovery_routes, monkeypatch
):
    file_path, source, config = recovery_routes
    original_read = Path.read_bytes

    def denied(path):
        if path == file_path:
            raise PermissionError("test source unreadable")
        return original_read(path)

    app = create_app(config, reload=True)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            assert (await client.get("/affected")).text == "A"
            with monkeypatch.context() as patch:
                patch.setattr(Path, "read_bytes", denied)
                response = await client.get("/affected")
                assert response.status_code == 500
                assert response.json()["exceptionType"] == "HandlerLoadError"
                assert (await client.get("/healthy")).text == "healthy"
                assert loader.handler_module_name(file_path) not in sys.modules
            file_path.write_text(source.replace("'A'", "'B'"), encoding="utf-8")
            await app.state.handler_watcher.scan_once()
            assert (await client.get("/affected")).text == "B"


@pytest.mark.asyncio
async def test_atomic_save_updates_http_response(recovery_routes, handler_factory):
    file_path, source, config = recovery_routes
    app = create_app(config, reload=True)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            assert (await client.get("/affected")).text == "A"
            replacement = handler_factory(source.replace("'A'", "'B'"), "replacement.py")
            replacement.replace(file_path)
            await app.state.handler_watcher.scan_once()
            assert (await client.get("/affected")).text == "B"
            assert (await client.get("/healthy")).text == "healthy"


@pytest.mark.asyncio
async def test_inflight_old_callable_finishes_after_fresh_request(
    handler_factory, config_factory, monkeypatch
):
    bridge = ModuleType("phase4_http_bridge")
    bridge.entered = asyncio.Event()
    bridge.release = asyncio.Event()
    monkeypatch.setitem(sys.modules, bridge.__name__, bridge)
    file_path = handler_factory(
        "from phase4_http_bridge import entered, release\n"
        "async def handler(event):\n"
        "    entered.set()\n"
        "    await release.wait()\n"
        "    return {'statusCode': 200, 'body': 'old'}\n"
    )
    app = create_app(load_config(config_factory(file_path)), reload=True)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            pending = asyncio.create_task(client.get("/test"))
            try:
                await asyncio.wait_for(bridge.entered.wait(), timeout=2)
                file_path.write_text(
                    "def handler(event): return {'statusCode': 200, 'body': 'new'}\n",
                    encoding="utf-8",
                )
                await app.state.handler_watcher.scan_once()
                assert (await client.get("/test")).text == "new"
                bridge.release.set()
                assert (await pending).text == "old"
            finally:
                bridge.release.set()
                await pending


@pytest.mark.asyncio
async def test_observer_startup_failure_propagates_without_accepting_requests(
    handler_factory, config_factory, monkeypatch
):
    watcher_module = importlib.import_module("zerodock.engine.watcher")
    file_path = handler_factory("def handler(event): return 'ok'\n")
    app = create_app(load_config(config_factory(file_path)), reload=True)

    def fail(paths):
        raise RuntimeError("observer startup failed")

    monkeypatch.setattr(watcher_module, "read_revisions", fail)
    with pytest.raises(RuntimeError, match="observer startup failed"):
        async with app.router.lifespan_context(app):
            pytest.fail("Application accepted startup with a failed observer")
    assert app.state.handler_watcher.task is None
    assert loader.handler_module_name(file_path) not in loader._module_states


@pytest.mark.asyncio
async def test_http_refresh_ignores_same_timestamp_bytecode(handler_factory, config_factory):
    source = "def handler(event): return {'statusCode': 200, 'body': 'A'}\n"
    file_path = handler_factory(source)
    py_compile.compile(str(file_path), doraise=True)
    original_stat = file_path.stat()
    app = create_app(load_config(config_factory(file_path)), reload=True)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            assert (await client.get("/test")).text == "A"
            file_path.write_text(source.replace("'A'", "'B'"), encoding="utf-8")
            os.utime(file_path, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
            await app.state.handler_watcher.scan_once()
            assert (await client.get("/test")).text == "B"


@pytest.mark.asyncio
async def test_shared_entrypoints_refresh_without_affecting_another_file(handler_factory):
    source = (
        "def first(event): return {'statusCode': 200, 'body': 'A1'}\n"
        "def second(event): return {'statusCode': 200, 'body': 'A2'}\n"
    )
    shared = handler_factory(source, "shared/handler.py")
    other = handler_factory(
        "def handler(event): return {'statusCode': 200, 'body': 'unchanged'}\n", "other/handler.py"
    )
    config = ServerlessConfig(
        routes={
            "/first": RouteDefinition(file=shared, handler="first"),
            "/second": RouteDefinition(file=shared, handler="second"),
            "/other": RouteDefinition(file=other),
        }
    )
    app = create_app(config, reload=True)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            for route, expected in (("/first", "A1"), ("/second", "A2"), ("/other", "unchanged")):
                assert (await client.get(route)).text == expected
            unrelated_module = sys.modules[loader.handler_module_name(other)]
            shared.write_text(source.replace("'A", "'B"), encoding="utf-8")
            assert await app.state.handler_watcher.scan_once() == (shared,)
            assert sys.modules[loader.handler_module_name(other)] is unrelated_module
            for route, expected in (("/first", "B1"), ("/second", "B2"), ("/other", "unchanged")):
                assert (await client.get(route)).text == expected


@pytest.mark.asyncio
@pytest.mark.parametrize("reload_enabled", [False, True])
async def test_app_forwards_reload_mode_to_loader(
    handler_factory, config_factory, reload_enabled, monkeypatch
):
    gateway = importlib.import_module("zerodock.gateway.app")
    original = gateway.load_handler
    modes = []

    def load(*args, **kwargs):
        modes.append(kwargs["reload"])
        return original(*args, **kwargs)

    monkeypatch.setattr(gateway, "load_handler", load)
    file_path = handler_factory("def handler(event): return {'statusCode': 200, 'body': 'ok'}\n")
    app = create_app(load_config(config_factory(file_path)), reload=reload_enabled)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            assert (await client.get("/test")).text == "ok"
        assert (app.state.handler_watcher is not None) is reload_enabled
    assert modes == [reload_enabled]


@pytest.mark.asyncio
async def test_automatic_detection_completes_within_500ms(
    handler_factory, config_factory, monkeypatch
):
    watcher_module = importlib.import_module("zerodock.engine.watcher")
    source = "def handler(event): return {'statusCode': 200, 'body': 'A'}\n"
    file_path = handler_factory(source)
    detected = asyncio.Event()
    original = watcher_module.invalidate_handler_cache

    def invalidate(module_name):
        original(module_name)
        detected.set()

    monkeypatch.setattr(watcher_module, "invalidate_handler_cache", invalidate)
    app = create_app(load_config(config_factory(file_path)), reload=True)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            assert (await client.get("/test")).text == "A"
            file_path.write_text(source.replace("'A'", "'B'"), encoding="utf-8")
            saved = time.perf_counter()
            await asyncio.wait_for(detected.wait(), timeout=2)
            duration_ms = (time.perf_counter() - saved) * 1000
            print(f"DETECTION_MS={duration_ms:.4f}; files=1; bytes={file_path.stat().st_size}")
            assert duration_ms <= 500
            assert (await client.get("/test")).text == "B"


@pytest.mark.asyncio
async def test_disabled_lifespan_never_constructs_an_observer(
    handler_factory, config_factory, monkeypatch
):
    gateway = importlib.import_module("zerodock.gateway.app")

    def forbidden(*args, **kwargs):
        raise AssertionError("Disabled application constructed an observer")

    monkeypatch.setattr(gateway, "HandlerWatcher", forbidden)
    file_path = handler_factory("def handler(event): return 'ok'\n")
    config = load_config(config_factory(file_path))
    enabled_app = gateway.create_app(config, reload=True)
    assert enabled_app.state.handler_watcher is None
    app = gateway.create_app(config)
    async with app.router.lifespan_context(app):
        assert app.state.handler_watcher is None


def test_importing_gateway_starts_no_observer(monkeypatch):
    gateway = importlib.import_module("zerodock.gateway.app")
    watcher_module = importlib.import_module("zerodock.engine.watcher")

    def forbidden(*args, **kwargs):
        raise AssertionError("Import constructed an observer")

    try:
        with monkeypatch.context() as patch:
            patch.setattr(watcher_module, "HandlerWatcher", forbidden)
            importlib.reload(gateway)
            assert gateway.app.state.handler_watcher is None
    finally:
        importlib.reload(gateway)


@pytest.mark.asyncio
async def test_config_outside_working_directory_keeps_handler_resolution(
    handler_factory, tmp_path, monkeypatch
):
    source = "def handler(event): return {'statusCode': 200, 'body': 'A'}\n"
    file_path = handler_factory(source, "project/functions/handler.py")
    config_path = tmp_path / "project/serverless-local.yaml"
    config_path.write_text("routes:\n  /test:\n    file: functions/handler.py\n", encoding="utf-8")
    working = tmp_path / "elsewhere"
    working.mkdir()
    monkeypatch.chdir(working)
    app = create_app(load_config(config_path), reload=True)
    async with app.router.lifespan_context(app):
        assert app.state.handler_watcher.paths == (file_path,)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            assert (await client.get("/test")).text == "A"
            file_path.write_text(source.replace("'A'", "'B'"), encoding="utf-8")
            await app.state.handler_watcher.scan_once()
            assert (await client.get("/test")).text == "B"


@pytest.mark.parametrize("reload_enabled", [False, True])
def test_initially_missing_handler_is_still_rejected(config_factory, tmp_path, reload_enabled):
    config_path = config_factory(tmp_path / "missing.py")
    with pytest.raises(ConfigurationError, match="does not exist"):
        create_app(load_config(config_path), reload=reload_enabled)


@pytest.mark.asyncio
@pytest.mark.parametrize("reload_enabled", [False, True])
async def test_module_globals_and_side_effects_are_per_request_and_after_shutdown(
    handler_factory, config_factory, monkeypatch, reload_enabled
):
    bridge = ModuleType("phase5_globals_bridge")
    bridge.calls = 0
    monkeypatch.setitem(sys.modules, bridge.__name__, bridge)
    file_path = handler_factory(
        "import phase5_globals_bridge as bridge\n"
        "bridge.calls += 1\n"
        "counter = globals().get('counter', 0) + 1\n"
        "def handler(event):\n"
        "    return {'statusCode': 200, 'body': {'counter': counter, 'calls': bridge.calls}}\n"
    )
    app = create_app(load_config(config_factory(file_path)), reload=reload_enabled)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            for expected_calls in (1, 2):
                assert (await client.get("/test")).json() == {"counter": 1, "calls": expected_calls}
    assert loader.handler_module_name(file_path) not in loader._module_states
    direct = loader.load_handler(file_path, "handler", reload=reload_enabled)
    assert direct({})["body"] == {"counter": 1, "calls": 3}


@pytest.mark.asyncio
@pytest.mark.parametrize("reload_enabled", [False, True])
async def test_repeated_application_lifespan_is_clean(
    handler_factory, config_factory, reload_enabled
):
    file_path = handler_factory("def handler(event): return 'ok'\n")
    app = create_app(load_config(config_factory(file_path)), reload=reload_enabled)
    previous = None
    for iteration in range(3):
        async with app.router.lifespan_context(app):
            current = app.state.handler_watcher
            if reload_enabled:
                assert current is not previous
                assert current.task is not None
                previous = current
        if reload_enabled:
            assert current.task is None
        assert loader.handler_module_name(file_path) not in loader._module_states


@pytest.mark.asyncio
async def test_one_application_shutdown_does_not_break_another(handler_factory):
    source = "def handler(event): return {'statusCode': 200, 'body': 'A'}\n"
    file_path = handler_factory(source)
    config = ServerlessConfig(routes={"/test": RouteDefinition(file=file_path)})
    first = create_app(config, reload=True)
    second = create_app(config, reload=True)
    module_name = loader.handler_module_name(file_path)
    async with second.router.lifespan_context(second):
        async with first.router.lifespan_context(first):
            assert loader._module_states[module_name].watcher_owners == 2
            state = loader._module_states[module_name]
            old = loader.load_handler(file_path, "handler", reload=True)
        assert loader._module_states[module_name] is state
        assert state.watcher_owners == 1
        assert sys.modules[module_name].handler is old
        file_path.write_text(source.replace("'A'", "'B'"), encoding="utf-8")
        await second.state.handler_watcher.scan_once()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=second), base_url="http://test"
        ) as client:
            assert (await client.get("/test")).text == "B"
    assert module_name not in loader._module_states


def test_shared_handler_apps_on_distinct_event_loops(handler_factory):
    source = "def handler(event): return {'statusCode': 200, 'body': 'A'}\n"
    file_path = handler_factory(source)
    config = ServerlessConfig(routes={"/test": RouteDefinition(file=file_path)})
    first_ready = threading.Event()
    second_ready = threading.Event()
    stop_first = threading.Event()
    refresh_second = threading.Event()

    def run(ready, release, refresh):
        async def session():
            app = create_app(config, reload=True)
            async with app.router.lifespan_context(app):
                loop_id = id(asyncio.get_running_loop())
                ready.set()
                assert await asyncio.to_thread(release.wait, 5)
                if refresh:
                    await app.state.handler_watcher.scan_once()
                    async with httpx.AsyncClient(
                        transport=httpx.ASGITransport(app=app), base_url="http://test"
                    ) as client:
                        assert (await client.get("/test")).text == "B"
            return loop_id

        return asyncio.run(session())

    with ThreadPoolExecutor(max_workers=2) as workers:
        first = workers.submit(run, first_ready, stop_first, False)
        second = workers.submit(run, second_ready, refresh_second, True)
        try:
            assert first_ready.wait(timeout=5)
            assert second_ready.wait(timeout=5)
            module_name = loader.handler_module_name(file_path)
            assert loader._module_states[module_name].watcher_owners == 2
            stop_first.set()
            first_loop = first.result(timeout=5)
            assert loader._module_states[module_name].watcher_owners == 1
            file_path.write_text(source.replace("'A'", "'B'"), encoding="utf-8")
            refresh_second.set()
            assert second.result(timeout=5) != first_loop
        finally:
            stop_first.set()
            refresh_second.set()
            with suppress(Exception):
                first.result(timeout=5)
            with suppress(Exception):
                second.result(timeout=5)
    assert loader.handler_module_name(file_path) not in loader._module_states


@pytest.mark.asyncio
@pytest.mark.parametrize("primary_error", [ValueError, asyncio.CancelledError])
async def test_lifespan_preserves_primary_error_when_cleanup_also_fails(
    handler_factory, config_factory, monkeypatch, caplog, primary_error
):
    gateway = importlib.import_module("zerodock.gateway.app")
    original_watcher = gateway.HandlerWatcher

    class FailedCleanup(original_watcher):
        async def stop(self):
            await super().stop()
            raise RuntimeError("secondary cleanup failure")

    monkeypatch.setattr(gateway, "HandlerWatcher", FailedCleanup)
    file_path = handler_factory("def handler(event): return 'ok'\n")
    app = create_app(load_config(config_factory(file_path)), reload=True)
    with caplog.at_level(logging.ERROR):
        with pytest.raises(primary_error):
            async with app.router.lifespan_context(app):
                raise primary_error("primary application failure")
    assert "cleanup" in caplog.text.lower()
    assert app.state.handler_watcher.task is None
    assert loader.handler_module_name(file_path) not in loader._module_states


@pytest.mark.asyncio
@pytest.mark.parametrize("reload_enabled", [False, True])
@pytest.mark.parametrize("prefix", ["", "async "])
async def test_request_context_and_response_contracts_remain_compatible(
    handler_factory, config_factory, reload_enabled, prefix
):
    file_path = handler_factory(
        f"{prefix}def handler(event, context):\n"
        "    return {'statusCode': 201, 'headers': {'X-Phase5': 'yes'}, 'body': {\n"
        "        'method': event['requestContext']['http']['method'],\n"
        "        'query': event['queryStringParameters'], 'body': event['body'],\n"
        "        'function': context.function_name, 'request_id': context.request_id,\n"
        "        'remaining': context.get_remaining_time_in_millis()}}\n"
    )
    app = create_app(load_config(config_factory(file_path)), reload=reload_enabled)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/test?name=phase5", json={"value": 1})
            assert response.status_code == 201
            assert response.headers["X-Phase5"] == "yes"
            body = response.json()
            assert body["method"] == "POST"
            assert body["query"] == {"name": "phase5"}
            assert json.loads(body["body"]) == {"value": 1}
            assert body["function"] == "handler"
            assert body["request_id"].startswith("zd-req-")
            assert 0 <= body["remaining"] <= 30000


@pytest.mark.asyncio
@pytest.mark.parametrize("reload_enabled", [False, True])
async def test_async_timeout_still_cancels_handler_and_returns_504(
    handler_factory, monkeypatch, reload_enabled
):
    bridge = ModuleType("phase5_timeout_bridge")
    bridge.cancelled = asyncio.Event()
    monkeypatch.setitem(sys.modules, bridge.__name__, bridge)
    file_path = handler_factory(
        "import asyncio\nfrom phase5_timeout_bridge import cancelled\n"
        "async def handler(event, context):\n"
        "    try:\n        await asyncio.Event().wait()\n"
        "    finally:\n        cancelled.set()\n"
    )
    config = ServerlessConfig(routes={"/test": RouteDefinition(file=file_path, timeout_seconds=1)})
    app = create_app(config, reload=reload_enabled)
    original_wait = asyncio.wait_for
    configured_timeouts = []

    async def short_handler_deadline(awaitable, timeout):
        code = getattr(awaitable, "cr_code", None)
        if code is not None and code.co_name == "handler":
            configured_timeouts.append(timeout)
            timeout = 0.005
        return await original_wait(awaitable, timeout)

    async with app.router.lifespan_context(app):
        with monkeypatch.context() as patch:
            patch.setattr(asyncio, "wait_for", short_handler_deadline)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/test")
        assert response.status_code == 504
        assert response.json()["error"] == "GatewayTimeout"
        assert bridge.cancelled.is_set()
        assert configured_timeouts == [1]
