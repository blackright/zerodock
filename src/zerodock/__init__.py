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
    # In an uninstalled/development checkout, resolve version dynamically from pyproject.toml
    try:
        import re
        from pathlib import Path

        _pyproject = Path(__file__).resolve().parent.parent.parent / "pyproject.toml"
        if _pyproject.exists():
            _m = re.search(r'version\s*=\s*"([^"]+)"', _pyproject.read_text(encoding="utf-8"))
            __version__ = _m.group(1) if _m else "0.0.0.dev0"
        else:
            __version__ = "0.0.0.dev0"
    except Exception:
        __version__ = "0.0.0.dev0"

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
