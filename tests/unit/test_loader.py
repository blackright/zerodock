"""Unit tests for ZeroDock dynamic module loader."""

import pytest
from pathlib import Path
from zerodock.engine.context import InvocationContext
from zerodock.engine.loader import load_handler, invoke_handler, HandlerLoadError


def test_load_and_invoke_sync_handler():
    """Verify loading and invoking standard two-argument sync handler."""
    handler_file = Path("tests/fixtures/handlers/hello.py").resolve()
    handler_fn = load_handler(handler_file, "lambda_handler")

    event = {"queryStringParameters": {"name": "Alice"}}
    context = InvocationContext(function_name="hello")

    result = invoke_handler(handler_fn, event, context)
    assert result["statusCode"] == 200
    assert result["body"]["message"] == "Hello, Alice!"
    assert result["body"]["requestId"] == context.request_id


def test_load_handler_missing_file():
    """Verify HandlerLoadError when source file does not exist."""
    missing_file = Path("tests/fixtures/handlers/not_found.py").resolve()
    with pytest.raises(HandlerLoadError, match="File not found"):
        load_handler(missing_file, "handler")


def test_load_handler_missing_function():
    """Verify HandlerLoadError when function name does not exist in module."""
    handler_file = Path("tests/fixtures/handlers/hello.py").resolve()
    with pytest.raises(HandlerLoadError, match="not found in module"):
        load_handler(handler_file, "non_existent_function")


def test_load_handler_not_callable(tmp_path: Path):
    """Verify HandlerLoadError when attribute is not a callable function."""
    var_file = tmp_path / "constant.py"
    var_file.write_text("my_var = 42\n", encoding="utf-8")

    with pytest.raises(HandlerLoadError, match="is not callable"):
        load_handler(var_file, "my_var")


@pytest.mark.asyncio
async def test_invoke_async_handler(tmp_path: Path):
    """Verify invoking coroutine async handler works seamlessly."""
    async_file = tmp_path / "async_fn.py"
    async_file.write_text(
        "async def async_handler(event, context):\n"
        "    return {'statusCode': 200, 'body': 'async result'}\n",
        encoding="utf-8",
    )
    handler_fn = load_handler(async_file, "async_handler")
    result = await invoke_handler(handler_fn, {}, None)
    assert result["body"] == "async result"


def test_invoke_single_arg_handler(tmp_path: Path):
    """Verify handler expecting only 'event' parameter is called without error."""
    single_arg_file = tmp_path / "single_arg.py"
    single_arg_file.write_text(
        "def single_handler(event):\n"
        "    return {'statusCode': 200, 'received': event.get('action')}\n",
        encoding="utf-8",
    )
    handler_fn = load_handler(single_arg_file, "single_handler")
    result = invoke_handler(handler_fn, {"action": "ping"}, None)
    assert result["received"] == "ping"
