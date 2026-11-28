"""Terminal UI (TUI) startup banner and live request latency monitor (issue #4).

Uses `rich` when installed and color output is enabled; gracefully falls back to
clean ANSI/plain-text formatting when `rich` is unavailable, `--plain` / `--no-color`
is passed, `NO_COLOR` is set, or the output stream is non-TTY.
"""

from __future__ import annotations

import os
import sys
from typing import TextIO

from zerodock import __version__
from zerodock.config.models import ServerlessConfig

_ANSI_RESET = "\x1b[0m"
_ANSI_GREEN = "\x1b[32m"
_ANSI_YELLOW = "\x1b[33m"
_ANSI_BOLD_RED = "\x1b[1;31m"
_ANSI_CYAN = "\x1b[36m"


def _is_plain(plain: bool, stream: TextIO) -> bool:
    if plain or os.environ.get("NO_COLOR"):
        return True
    isatty = getattr(stream, "isatty", None)
    return not bool(isatty and isatty())


def _status_style(status: int) -> tuple[str, str]:
    if 200 <= status < 300:
        return "green", _ANSI_GREEN
    if 400 <= status < 500:
        return "yellow", _ANSI_YELLOW
    if status >= 500:
        return "bold red", _ANSI_BOLD_RED
    return "cyan", _ANSI_CYAN


def _format_plain_table(config: ServerlessConfig, version: str) -> str:
    host = config.gateway.host
    port = config.gateway.port
    lines = [
        f"ZeroDock v{version} | http://{host}:{port}",
        "-" * 60,
        f"{'ROUTE':<22} {'METHODS':<16} HANDLER",
        "-" * 60,
    ]
    for route_path, defn in config.routes.items():
        methods = ",".join(defn.methods)
        target = f"{defn.file}:{defn.handler}"
        lines.append(f"{route_path:<22} {methods:<16} {target}")
    lines.append("-" * 60)
    return "\n".join(lines) + "\n"


def render_startup_banner(
    config: ServerlessConfig,
    *,
    version: str | None = None,
    plain: bool = False,
    stream: TextIO | None = None,
) -> None:
    """Render the startup banner and registered routes table."""
    target_stream = stream if stream is not None else sys.stdout
    ver = version or __version__
    use_plain = _is_plain(plain, target_stream)

    if not use_plain:
        try:
            from rich.console import Console
            from rich.table import Table

            console = Console(file=target_stream, force_terminal=True)
            console.print(
                f"[bold cyan]ZeroDock v{ver}[/bold cyan] "
                f"listening on [bold]http://{config.gateway.host}:{config.gateway.port}[/bold]"
            )
            table = Table(title="Registered Routes")
            table.add_column("Route", style="cyan")
            table.add_column("Methods", style="magenta")
            table.add_column("Handler", style="green")
            for route_path, defn in config.routes.items():
                table.add_row(route_path, ", ".join(defn.methods), f"{defn.file}:{defn.handler}")
            console.print(table)
            return
        except ImportError:
            pass

    target_stream.write(_format_plain_table(config, ver))
    target_stream.flush()


def format_request_log(
    method: str,
    path: str,
    status: int,
    duration_ms: float,
    *,
    plain: bool = False,
) -> str:
    """Format a single request log line with status badge and latency in ms."""
    duration_str = f"{duration_ms:.1f}ms"
    if plain:
        return f"{method.upper():<6} {path} -> {status} ({duration_str})"
    _, ansi = _status_style(status)
    return f"{method.upper():<6} {path} -> {ansi}{status}{_ANSI_RESET} ({duration_str})"


def render_request_log(
    method: str,
    path: str,
    status: int,
    duration_ms: float,
    *,
    plain: bool = False,
    stream: TextIO | None = None,
) -> None:
    """Write a color-coded (or plain-text) request log line."""
    target_stream = stream if stream is not None else sys.stdout
    use_plain = _is_plain(plain, target_stream)
    line = format_request_log(method, path, status, duration_ms, plain=use_plain)
    target_stream.write(line + "\n")
    target_stream.flush()
