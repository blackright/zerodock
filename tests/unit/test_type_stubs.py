"""Unit tests for PEP 561 py.typed marker and type annotation integrity."""

from pathlib import Path

from zerodock.config.models import GatewayConfig, RouteDefinition, ServerlessConfig
from zerodock.engine.context import InvocationContext, InvocationResult


def test_py_typed_marker_exists() -> None:
    """The PEP 561 py.typed marker file must exist in the src/zerodock package directory."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    py_typed = repo_root / "src" / "zerodock" / "py.typed"
    assert py_typed.exists(), "src/zerodock/py.typed must exist for PEP 561 compliance"


def test_core_models_have_type_annotations() -> None:
    """Core public data models must maintain explicit type annotations on all fields."""
    # Check GatewayConfig type annotations
    assert "host" in GatewayConfig.__annotations__
    assert "port" in GatewayConfig.__annotations__
    assert "log_level" in GatewayConfig.__annotations__

    # Check ServerlessConfig type annotations
    assert "version" in ServerlessConfig.__annotations__
    assert "gateway" in ServerlessConfig.__annotations__
    assert "routes" in ServerlessConfig.__annotations__

    # Check RouteDefinition type annotations
    assert "file" in RouteDefinition.__annotations__
    assert "handler" in RouteDefinition.__annotations__
    assert "methods" in RouteDefinition.__annotations__
    assert "timeout_seconds" in RouteDefinition.__annotations__

    # Check InvocationContext type annotations
    assert "function_name" in InvocationContext.__annotations__
    assert "request_id" in InvocationContext.__annotations__
    assert "memory_limit_in_mb" in InvocationContext.__annotations__
    assert "timeout_seconds" in InvocationContext.__annotations__


def test_invocation_result_typing() -> None:
    """InvocationResult must define typed response attributes."""
    assert "status_code" in InvocationResult.__annotations__
    assert "headers" in InvocationResult.__annotations__
    assert "body" in InvocationResult.__annotations__
    assert "is_base64_encoded" in InvocationResult.__annotations__
