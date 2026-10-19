"""ZeroDock - Ultra-lightweight local serverless execution engine."""

from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from zerodock.config.models import GatewayConfig, RouteDefinition, ServerlessConfig
    from zerodock.engine.context import InvocationContext, InvocationResult
    from zerodock.gateway.app import create_app
    from zerodock.gateway.server import run_server

try:
    __version__ = version("zerodock")
except PackageNotFoundError:
    __version__ = "0.1.1"

__all__ = [
    "__version__",
    "create_app",
    "run_server",
    "GatewayConfig",
    "RouteDefinition",
    "ServerlessConfig",
    "InvocationContext",
    "InvocationResult",
]


def __getattr__(name: str) -> Any:
    """Lazy-load public symbols to preserve sub-millisecond module import times."""
    if name == "create_app":
        from zerodock.gateway.app import create_app
        return create_app
    if name == "run_server":
        from zerodock.gateway.server import run_server
        return run_server
    if name in {"GatewayConfig", "RouteDefinition", "ServerlessConfig"}:
        import zerodock.config.models as models
        return getattr(models, name)
    if name in {"InvocationContext", "InvocationResult"}:
        import zerodock.engine.context as context
        return getattr(context, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
