"""Unit tests for ZeroDock configuration parsing and models."""

from pathlib import Path

import pytest

from zerodock.config.models import GatewayConfig, RouteDefinition, ServerlessConfig
from zerodock.config.parser import ConfigurationError, load_config
from zerodock.engine.context import InvocationContext, InvocationResult


def test_gateway_config_defaults():
    """Verify GatewayConfig defaults adhere to specification."""
    gw = GatewayConfig()
    assert gw.host == "127.0.0.1"
    assert gw.port == 8080
    assert gw.log_level == "info"


def test_route_definition_normalization():
    """Verify methods and handler names are normalized and validated."""
    route = RouteDefinition(
        file=Path("./test.py"),
        handler="my_handler",
        methods=["get", "post"],
    )
    assert route.methods == ["GET", "POST"]
    assert route.handler == "my_handler"
    assert route.timeout_seconds == 30


def test_route_definition_invalid_handler():
    """Verify invalid Python identifiers are rejected."""
    with pytest.raises(ValueError, match="not a valid Python identifier"):
        RouteDefinition(file=Path("./test.py"), handler="123_invalid-name")


def test_route_definition_invalid_method():
    """Verify unsupported HTTP methods are rejected."""
    with pytest.raises(ValueError, match="Invalid HTTP method"):
        RouteDefinition(file=Path("./test.py"), methods=["INVALID_METHOD"])


def test_serverless_config_path_normalization():
    """Verify route paths get a leading slash and trailing slash removed."""
    cfg = ServerlessConfig(
        routes={
            "api/users": RouteDefinition(file=Path("./users.py")),
            "/api/orders/": RouteDefinition(file=Path("./orders.py")),
        }
    )
    assert "/api/users" in cfg.routes
    assert "/api/orders" in cfg.routes


def test_load_valid_config_fixture():
    """Verify loading valid fixture resolves absolute paths correctly."""
    fixture_path = Path("tests/fixtures/configs/valid.yaml")
    config = load_config(fixture_path)

    assert config.version == "1.0"
    assert config.gateway.host == "127.0.0.1"
    assert config.gateway.port == 8080
    assert "/api/hello" in config.routes

    route = config.routes["/api/hello"]
    assert route.file.is_absolute()
    assert route.file.name == "hello.py"
    assert route.handler == "lambda_handler"
    assert "GET" in route.methods


def test_load_config_missing_file():
    """Verify ConfigurationError on missing file."""
    with pytest.raises(ConfigurationError, match="Configuration file not found"):
        load_config("non_existent_file.yaml")


def test_load_config_malformed_yaml(tmp_path: Path):
    """Verify ConfigurationError on syntax error in YAML."""
    broken_yaml = tmp_path / "broken.yaml"
    broken_yaml.write_text("routes:\n  bad_indent:\n- unaligned", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="Malformed YAML"):
        load_config(broken_yaml)


def test_load_config_empty_routes(tmp_path: Path):
    """Verify ConfigurationError when routes is empty."""
    empty_routes = tmp_path / "empty.yaml"
    empty_routes.write_text("routes: {}", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="Configuration validation failed"):
        load_config(empty_routes)


def test_invocation_context_remaining_time():
    """Verify InvocationContext computes remaining milliseconds accurately."""
    ctx = InvocationContext(function_name="hello", timeout_seconds=5)
    remaining = ctx.get_remaining_time_in_millis()
    assert 4800 <= remaining <= 5000
    assert ctx.request_id.startswith("zd-req-")


def test_invocation_result_defaults():
    """Verify InvocationResult default values."""
    res = InvocationResult(body={"status": "ok"})
    assert res.status_code == 200
    assert res.headers["Content-Type"] == "application/json"
    assert res.body == {"status": "ok"}
