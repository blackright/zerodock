"""Command-line interface (CLI) for ZeroDock."""

import argparse
import sys

from zerodock import __version__
from zerodock.gateway.server import run_server


def build_parser() -> argparse.ArgumentParser:
    """Creates the top-level argument parser for the zerodock CLI."""
    parser = argparse.ArgumentParser(
        prog="zerodock",
        description="ZeroDock - Ultra-lightweight local serverless execution engine.",
    )
    parser.add_argument("-v", "--version", action="version", version=f"ZeroDock {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # 'dev' command
    dev_parser = subparsers.add_parser("dev", help="Start the local serverless HTTP gateway")
    dev_parser.add_argument(
        "-c",
        "--config",
        default="serverless-local.yaml",
        help="Path to serverless-local.yaml (default: serverless-local.yaml)",
    )
    dev_parser.add_argument(
        "--host",
        default=None,
        help="Host IP to bind (overrides config gateway.host)",
    )
    dev_parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=None,
        help="Port number to bind (overrides config gateway.port)",
    )
    dev_parser.add_argument(
        "--log-level",
        default=None,
        choices=["debug", "info", "warning", "error"],
        help="Logging level verbosity",
    )
    dev_parser.add_argument(
        "--reload",
        action="store_true",
        help="Observe handler changes in-process without restarting the gateway",
    )

    return parser


def main() -> None:
    """Main entrypoint for zerodock CLI."""
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "dev" or args.command is None:
        # If no subcommand passed, default to 'dev' if serverless-local.yaml exists
        config_path = getattr(args, "config", "serverless-local.yaml")
        host = getattr(args, "host", None)
        port = getattr(args, "port", None)
        log_level = getattr(args, "log_level", None)
        reload = getattr(args, "reload", False)

        try:
            run_server(
                config_path=config_path,
                host=host,
                port=port,
                log_level=log_level,
                reload=reload,
            )
        except Exception as exc:
            print(f"[ZeroDock Error] {exc}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
