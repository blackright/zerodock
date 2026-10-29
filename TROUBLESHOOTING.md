# Troubleshooting ZeroDock

Start with the smallest reproducible configuration and one handler. Keep the server
terminal visible and confirm which Python environment is running the command.

## Command not found

If `zerodock` is not on PATH, use the interpreter where the package was installed:

```bash
python -m zerodock.cli --version
python -m zerodock.cli dev
```

If Python reports that the module is missing, activate the intended environment or
use its executable directly. For example, in Windows PowerShell:

```powershell
& './.venv/Scripts/python.exe' -m zerodock.cli dev
```

Avoid adding a guessed, version-specific directory to your permanent PATH.
[Contributor setup](CONTRIBUTING.md#development-environment) explains activation.

## Configuration file not found

The default configuration path is `serverless-local.yaml` in the current working
directory. Supply the correct path when running elsewhere:

```bash
python -m zerodock.cli dev --config ./configs/serverless-local.yaml
```

The current parser reports `Configuration file not found at: ...`.
Handler paths inside the YAML are resolved relative to that YAML file's directory.

## Handler file missing at startup

Every configured target file must exist before startup. Check the path relative to
the configuration directory and ensure the quickstart does not reference files you
have not created.

A file deleted after a reload-enabled server starts is a different case: requests
to that route fail until valid source is recreated. The server can then recover
without restarting.

## Port already in use

Choose an available port:

```bash
python -m zerodock.cli dev --port 8081
```

Do not terminate an unfamiliar process merely because it owns the old port.
If investigating a process, verify its identity and ownership first.

## Reload flag not recognized

Check the environment's actual options:

```bash
python -m zerodock.cli dev --help
```

The syntax is `dev --reload`, not a top-level `--reload`. If the option is absent,
the installed release may predate the checkout's implementation. Follow the
[installation guidance](README.md#installation-and-release-status) for current source.

## A saved change is not visible

1. Confirm the server started with `dev --reload`.
2. Confirm the edited file is a configured handler, not just an imported helper.
3. Wait for the invalidation log before asserting the next response is fresh.
4. Check for syntax/import errors, the correct callable name, and unreadable files.
5. Restart for changed configuration, new routes, or imported-helper changes.

Do not recursively delete caches or remove unrelated modules as a workaround.
See [the reload contract](docs/hot-reload.md).

## Request returns HTTP 500

Handler execution, import, entrypoint, or response conversion may have failed.
The development response uses this shape; values vary by exception:

```json
{
  "error": "InternalServerError",
  "exceptionType": "HandlerLoadError",
  "message": "Diagnostic message",
  "requestId": "zd-req-example"
}
```

Read the server traceback and fix the original failure. A valid save can recover
under reload without a stale-success fallback. Error details can expose sensitive
information: do not serve this development gateway to untrusted clients.

## Request returns HTTP 504 or blocks the gateway

Awaited asynchronous handler execution is subject to the configured timeout.
Blocking synchronous work executes inline and cannot be forcibly interrupted by
that asynchronous timeout. It can also delay other requests and file observation.

The context's memory-limit value is metadata, not an enforced operating-system
memory limit. See [handler execution limits](docs/handlers.md#execution-limits).

## Request-body or query-parameter errors

`event["body"]` is a string or `None`, not an automatically parsed JSON object.
Decode JSON explicitly and account for `isBase64Encoded` when handling binary data.

Query parameters may be `None`. Use:

```python
parameters = event.get("queryStringParameters") or {}
name = parameters.get("name", "World")
```

The method is in `event["requestContext"]["http"]["method"]`; the current event does
not provide the older documented `httpMethod` field.
See [the event reference](docs/handlers.md#event-reference).

## Breakpoint does not stop execution

Run the gateway under the intended interpreter/debugger and send a request to the
configured handler. Merely opening a file or placing a visual breakpoint does not
attach an IDE debugger to an already-running process.

Check `PYTHONBREAKPOINT` and your IDE configuration if built-in breakpoints are
disabled. Continue from the debugger before expecting the request to finish.
[Debugging guidance](docs/hot-reload.md#debugging) includes terminal and IDE setup.

## Shutdown appears stuck

An active request, paused debugger, or outstanding file read can delay shutdown.
Reload cleanup drains its owned file observation; it does not forcibly cancel a
hung filesystem operation. Do not assume cancelling an await terminated a worker.

Resume paused debugging first. Record the filesystem, runtime, last log messages,
and a minimal reproduction if the server still cannot stop normally.

## JSON response serialization fails

Return JSON-compatible objects. Convert values such as datetimes explicitly:

```python
from datetime import datetime, timezone

def lambda_handler(event, context):
    return {"timestamp": datetime.now(timezone.utc).isoformat()}
```

## Reporting a problem

Include versions, sanitized configuration, a minimal handler, exact commands,
expected/actual results, and redacted logs. Never attach credentials, complete
environment dumps, or private request payloads.

Use the [issue tracker](https://github.com/blackright/zerodock/issues).
For performance reports, include the boundaries and workload described in
[Performance and validation](docs/performance.md).
