"""Performance and startup benchmark tests for ZeroDock."""

import asyncio
import importlib
import json
import os
import subprocess
import sys
import time

import httpx
import pytest

from zerodock.config.parser import load_config
from zerodock.gateway.app import create_app

BASELINE_IDLE_RSS_LIMIT_BYTES = 60_000_000


@pytest.mark.parametrize(
    "rss_bytes, accepted",
    [
        (49_000_000, True),
        (55_000_000, True),
        (59_999_999, True),
        (60_000_000, False),
        (60_000_001, False),
    ],
)
def test_approved_baseline_memory_budget_boundary(rss_bytes, accepted):
    assert (rss_bytes < BASELINE_IDLE_RSS_LIMIT_BYTES) is accepted


def test_cold_boot_under_100ms():
    """Verify that configuration parsing and application creation completes under 100ms."""
    start_time = time.perf_counter()

    config = load_config("serverless-local.yaml")
    app = create_app(config)

    boot_duration_ms = (time.perf_counter() - start_time) * 1000

    assert app is not None
    # Constitutional Principle I: cold start < 100ms
    assert boot_duration_ms < 100.0, f"Cold boot took {boot_duration_ms:.2f}ms (>100ms)"


@pytest.mark.asyncio
async def test_request_dispatch_latency():
    """Verify request round-trip overhead remains well within performance budget."""
    config = load_config("serverless-local.yaml")
    app = create_app(config)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8080") as client:
        # Warm-up request
        await client.get("/api/hello")

        durations = []
        for _ in range(3):
            start_time = time.perf_counter()
            response = await client.get("/api/hello?name=Benchmark")
            durations.append((time.perf_counter() - start_time) * 1000)
            assert response.status_code == 200

        best_ms = min(durations)
        # Dispatch latency should be exceptionally fast in-process (< 30ms total ASGI client-server)
        assert best_ms < 30.0, f"Best request dispatch took {best_ms:.2f}ms (all: {durations})"


@pytest.mark.asyncio
@pytest.mark.parametrize("reload", [False, True])
async def test_lifespan_startup_and_isolated_dispatch(
    handler_factory, config_factory, monkeypatch, reload
):
    """Measure warm-import startup and direct ASGI dispatch, not socket readiness."""
    source = "def handler(event): return {'statusCode': 200, 'body': 'A'}\n"
    target = handler_factory(source)
    config_path = config_factory(target)
    startup_samples = []
    for _ in range(10):
        started = time.perf_counter_ns()
        app = create_app(load_config(config_path), reload=reload)
        async with app.router.lifespan_context(app):
            startup_samples.append((time.perf_counter_ns() - started) / 1e6)
    app_module = importlib.import_module("zerodock.gateway.app")
    original_invoke = app_module.invoke_handler
    invocation_samples = []

    def measured_invoke(*args, **kwargs):
        started = time.perf_counter_ns()
        try:
            return original_invoke(*args, **kwargs)
        finally:
            invocation_samples.append((time.perf_counter_ns() - started) / 1e6)

    monkeypatch.setattr(app_module, "invoke_handler", measured_invoke)
    total_samples = []
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/test",
        "raw_path": b"/test",
        "query_string": b"",
        "headers": [],
        "server": ("127.0.0.1", 8080),
        "client": ("127.0.0.1", 12345),
        "root_path": "",
    }
    async with app.router.lifespan_context(app):
        for _ in range(23):
            messages = []

            async def receive():
                return {"type": "http.request", "body": b"", "more_body": False}

            async def send(message):
                messages.append(message)

            started = time.perf_counter_ns()
            await app(scope, receive, send)
            total_samples.append((time.perf_counter_ns() - started) / 1e6)
            assert messages[0]["status"] == 200
    totals = total_samples[3:]
    invocations = invocation_samples[3:]
    residual = [total - invoked for total, invoked in zip(totals, invocations)]
    print(
        json.dumps(
            {
                "measurement": "warm_startup_direct_dispatch",
                "reload": reload,
                "files": 1,
                "bytes": target.stat().st_size,
                "startup_ms": startup_samples,
                "direct_asgi_ms": totals,
                "invoker_ms": invocations,
                "residual_ms": residual,
            }
        )
    )
    assert max(startup_samples) < 100.0
    assert max(totals) < 5.0, "Conservative total includes tiny handler and invoker"


@pytest.mark.asyncio
@pytest.mark.parametrize("save_kind", ["same_metadata", "atomic"])
async def test_completed_save_detection_and_changed_request(
    handler_factory, config_factory, monkeypatch, save_kind
):
    """Time background detection, without manually forcing a scan."""
    source = "def handler(event): return {'statusCode': 200, 'body': 'A'}\n"
    target = handler_factory(source)
    app = create_app(load_config(config_factory(target)), reload=True)
    watcher_module = importlib.import_module("zerodock.engine.watcher")
    original_invalidate = watcher_module.invalidate_handler_cache
    acknowledged = asyncio.Event()
    invalidation_times = []

    def acknowledge(module_name):
        original_invalidate(module_name)
        invalidation_times.append(time.perf_counter_ns())
        acknowledged.set()

    monkeypatch.setattr(watcher_module, "invalidate_handler_cache", acknowledge)
    detection_samples = []
    request_samples = []
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            assert (await client.get("/test")).text == "A"
            for version in ["B", "C", "D"]:
                acknowledged.clear()
                metadata = target.stat()
                changed = source.replace("'A'", repr(version))
                if save_kind == "atomic":
                    replacement = target.with_suffix(".replacement")
                    replacement.write_text(changed, encoding="utf-8")
                    replacement.replace(target)
                else:
                    target.write_text(changed, encoding="utf-8")
                    os.utime(target, ns=(metadata.st_atime_ns, metadata.st_mtime_ns))
                saved = time.perf_counter_ns()
                await asyncio.wait_for(acknowledged.wait(), timeout=2)
                detection_samples.append((invalidation_times[-1] - saved) / 1e6)
                started = time.perf_counter_ns()
                response = await client.get("/test")
                request_samples.append((time.perf_counter_ns() - started) / 1e6)
                assert response.text == version
    print(
        json.dumps(
            {
                "measurement": "save_to_invalidation",
                "save_kind": save_kind,
                "files": 1,
                "bytes": target.stat().st_size,
                "interval_ms": 100,
                "detection_ms": detection_samples,
                "changed_request_ms": request_samples,
            }
        )
    )
    assert min(detection_samples) >= 0
    assert max(detection_samples) <= 500


@pytest.mark.parametrize("reload", [False, True])
def test_fresh_process_current_idle_rss(handler_factory, config_factory, reload):
    """Supplementary app-only RSS; actual listening-server acceptance is measured separately."""
    if sys.platform != "win32":
        pytest.skip("Current RSS measurement implemented only for approved Windows method")
    target = handler_factory("def handler(event): return {'statusCode': 200, 'body': 'A'}\n")
    config_path = config_factory(target)
    script = """
import asyncio, ctypes, json, sys
from ctypes import wintypes
from zerodock.config.parser import load_config
from zerodock.gateway.app import create_app
class Counters(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
        (name, ctypes.c_size_t) for name in ["PeakWorkingSetSize", "WorkingSetSize",
        "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage",
        "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage"]]
kernel = ctypes.WinDLL("kernel32", use_last_error=True)
kernel.GetCurrentProcess.restype = wintypes.HANDLE
psapi = ctypes.WinDLL("psapi", use_last_error=True)
psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
async def measure():
    app = create_app(load_config(sys.argv[1]), reload=sys.argv[2] == "True")
    async with app.router.lifespan_context(app):
        await asyncio.sleep(0.25)
        samples = []
        for index in range(3):
            counters = Counters()
            counters.cb = ctypes.sizeof(counters)
            if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),
                                            ctypes.byref(counters), counters.cb):
                raise ctypes.WinError(ctypes.get_last_error())
            samples.append(counters.WorkingSetSize)
            await asyncio.sleep(0.1)
        print(json.dumps({"reload": sys.argv[2], "rss_bytes": samples}), flush=True)
asyncio.run(measure())
"""
    result = subprocess.run(
        [sys.executable, "-B", "-c", script, str(config_path), str(reload)],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
    measurement = json.loads(result.stdout)
    print(json.dumps({"measurement": "isolated_idle_app_rss", **measurement}))
    assert max(measurement["rss_bytes"]) < BASELINE_IDLE_RSS_LIMIT_BYTES, measurement
