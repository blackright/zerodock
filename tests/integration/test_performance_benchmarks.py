"""Performance and startup benchmark tests for ZeroDock."""

import time
from pathlib import Path
import pytest
import httpx
from zerodock.config.parser import load_config
from zerodock.gateway.app import create_app


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

        # Measured request
        start_time = time.perf_counter()
        response = await client.get("/api/hello?name=Benchmark")
        duration_ms = (time.perf_counter() - start_time) * 1000

        assert response.status_code == 200
        # Dispatch latency should be exceptionally fast in-process (< 15ms total ASGI client-server)
        assert duration_ms < 15.0, f"Request dispatch took {duration_ms:.2f}ms"
