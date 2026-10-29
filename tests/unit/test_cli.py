"""Reload CLI and server forwarding contracts without opening sockets."""

import inspect
import sys
from unittest.mock import Mock

import pytest

from zerodock import cli
from zerodock.engine.loader import load_handler
from zerodock.gateway import server
from zerodock.gateway.app import create_app


@pytest.mark.parametrize("arguments, expected", [(["dev"], False), (["dev", "--reload"], True)])
def test_parser_reload_opt_in(arguments, expected):
    assert cli.build_parser().parse_args(arguments).reload is expected


@pytest.mark.parametrize(
    "arguments, expected", [([], False), (["dev"], False), (["dev", "--reload"], True)]
)
def test_main_forwards_reload(arguments, expected, monkeypatch):
    run = Mock()
    monkeypatch.setattr(cli, "run_server", run)
    monkeypatch.setattr(sys, "argv", ["zerodock", *arguments])
    cli.main()
    assert run.call_args.kwargs["reload"] is expected
    assert run.call_args.kwargs["config_path"] == "serverless-local.yaml"


@pytest.mark.parametrize("reload_enabled", [False, True])
def test_server_forwards_reload_to_app_not_uvicorn(
    handler_factory, config_factory, monkeypatch, reload_enabled
):
    config_path = config_factory(handler_factory("def handler(event): return 'ok'\n"))
    app = object()
    create = Mock(return_value=app)
    run = Mock()
    monkeypatch.setattr(server, "create_app", create)
    monkeypatch.setattr(server.uvicorn, "run", run)
    server.run_server(str(config_path), "127.0.0.1", 7777, "warning", reload=reload_enabled)
    assert create.call_args.kwargs == {"reload": reload_enabled}
    assert run.call_args.args == (app,)
    assert run.call_args.kwargs == {"host": "127.0.0.1", "port": 7777, "log_level": "warning"}


@pytest.mark.parametrize("function", [load_handler, create_app, server.run_server])
def test_reload_library_arguments_are_keyword_only(function):
    parameter = inspect.signature(function).parameters["reload"]
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert parameter.default is False


def test_legacy_server_positional_arguments_remain_supported(
    handler_factory, config_factory, monkeypatch
):
    config_path = config_factory(handler_factory("def handler(event): return 'ok'\n"))
    create = Mock(return_value=object())
    run = Mock()
    monkeypatch.setattr(server, "create_app", create)
    monkeypatch.setattr(server.uvicorn, "run", run)
    server.run_server(str(config_path), "127.0.0.1", 8123, "debug")
    assert create.call_args.kwargs == {"reload": False}
    assert run.call_args.kwargs == {"host": "127.0.0.1", "port": 8123, "log_level": "debug"}


@pytest.mark.parametrize("reload_enabled", [False, True])
def test_existing_cli_options_keep_their_values(monkeypatch, reload_enabled):
    arguments = [
        "zerodock",
        "dev",
        "-c",
        "custom.yaml",
        "--host",
        "127.0.0.2",
        "-p",
        "8123",
        "--log-level",
        "warning",
    ]
    if reload_enabled:
        arguments.append("--reload")
    run = Mock()
    monkeypatch.setattr(sys, "argv", arguments)
    monkeypatch.setattr(cli, "run_server", run)
    cli.main()
    assert run.call_args.kwargs == {
        "config_path": "custom.yaml",
        "host": "127.0.0.2",
        "port": 8123,
        "log_level": "warning",
        "reload": reload_enabled,
    }


def test_top_level_reload_is_not_silently_added():
    with pytest.raises(SystemExit) as error:
        cli.build_parser().parse_args(["--reload"])
    assert error.value.code == 2
