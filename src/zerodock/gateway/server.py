"""Embedded Uvicorn server runner for ZeroDock."""

from pathlib import Path
from typing import Optional
import uvicorn

from zerodock.config.parser import load_config
from zerodock.gateway.app import create_app


def run_server(
    config_path: str = "serverless-local.yaml",
    host: Optional[str] = None,
    port: Optional[int] = None,
    log_level: Optional[str] = None,
) -> None:
    """Boots the ZeroDock local serverless HTTP gateway.

    Args:
        config_path: Path to serverless-local.yaml.
        host: Optional host override (e.g. '127.0.0.1').
        port: Optional port override (e.g. 8080).
        log_level: Optional log level override ('info', 'debug', etc.).
    """
    config = load_config(config_path)

    bind_host = host or config.gateway.host
    bind_port = port or config.gateway.port
    server_log_level = log_level or config.gateway.log_level

    app = create_app(config)

    print(f"[ZeroDock] Booting local gateway on http://{bind_host}:{bind_port}")
    print(f"[ZeroDock] Loaded {len(config.routes)} registered route(s):")
    for path, route in config.routes.items():
        methods_str = ", ".join(route.methods)
        print(f"  - [{methods_str}] {path} -> {route.file.name}:{route.handler}")

    uvicorn.run(
        app,
        host=bind_host,
        port=bind_port,
        log_level=server_log_level,
    )
