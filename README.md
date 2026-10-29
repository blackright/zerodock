# ZeroDock

Run Python serverless-style HTTP handlers locally, without Docker or a cloud deployment.

[![PyPI](https://img.shields.io/pypi/v/zerodock.svg)](https://pypi.org/project/zerodock/)
[![CI](https://github.com/blackright/zerodock/actions/workflows/ci.yml/badge.svg)](https://github.com/blackright/zerodock/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

ZeroDock maps routes from a small YAML file to Python functions. It runs those
functions in your local Python process and returns their results over HTTP.

## What it provides

- A local HTTP gateway with synchronous and asynchronous Python handlers.
- A configuration file for routes, methods, entrypoints, and request timeouts.
- Opt-in, in-process reload of configured handler source files.
- Native Python debugging and structured development error responses.

ZeroDock is a local development tool, not a complete cloud emulator or a sandbox.
Cloud-specific adapters, service mocks, and other languages are future work.
See the [roadmap](docs/roadmap.md) and [security notes](docs/security.md).

## Installation and release status

The package declares Python 3.10 or later. Actual validation coverage and dependency
limitations are documented in [Performance and validation](docs/performance.md).

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it in **Windows PowerShell**:

```powershell
.\.venv\Scripts\Activate.ps1
```

Or in **macOS/Linux shells**:

```bash
source .venv/bin/activate
```

Install a published release:

```bash
python -m pip install zerodock
```

This documentation describes the current checkout. A published release may not
contain every feature shown here. To use the current source instead, run the
following from your cloned repository:

```bash
python -m pip install -e .
```

Use `python -m zerodock.cli --version` and
`python -m zerodock.cli dev --help` to inspect the environment you are actually using.
Contributor setup is covered in [CONTRIBUTING.md](CONTRIBUTING.md).

## Quickstart

### 1. Create one handler

In your project directory, create a `functions` directory and save this as
`functions/hello.py`:

```python
def lambda_handler(event, context):
    parameters = event.get("queryStringParameters") or {}
    name = parameters.get("name", "World")
    return {
        "statusCode": 200,
        "body": {"message": f"Hello, {name}!"},
    }
```

### 2. Configure its route

Save this as `serverless-local.yaml` beside the `functions` directory:

```yaml
version: "1.0"
gateway:
  host: "127.0.0.1"
  port: 8080
routes:
  /api/hello:
    file: "./functions/hello.py"
    handler: "lambda_handler"
    methods: ["GET"]
```

Handler paths are relative to the configuration file, not necessarily the directory
where the command is run. Every configured handler file must exist at startup.

### 3. Start the gateway

From the directory containing that configuration:

```bash
python -m zerodock.cli dev
```

Open this URL in a browser:

```text
http://127.0.0.1:8080/api/hello?name=Developer
```

Expected JSON response:

```json
{"message": "Hello, Developer!"}
```

Press Ctrl+C in the server terminal to stop the gateway.

### 4. Enable reload when available

If `dev --help` lists `--reload`, restart with:

```bash
python -m zerodock.cli dev --reload
```

Change the handler's greeting, save the file, wait for the invalidation log, and
request the same URL again. The running process and port stay unchanged.

Reload is disabled by default and watches configured handler files only. Imported
helpers, dependencies, configuration changes, and new routes may require a restart.
See [Hot reload and debugging](docs/hot-reload.md) for the full contract.

## Command reference

After installation, `zerodock` and `python -m zerodock.cli` are equivalent entrypoints.

| Command or option | Behavior |
| --- | --- |
| `zerodock dev` | Start using `serverless-local.yaml` |
| `zerodock dev --reload` | Enable in-process handler observation |
| `dev -c PATH`, `dev --config PATH` | Use another configuration file |
| `dev --host HOST` | Override the configured bind address |
| `dev -p PORT`, `dev --port PORT` | Override the configured port |
| `dev --log-level LEVEL` | Select debug, info, warning, or error logging |
| `zerodock --version` | Print the installed/resolved package version |
| `zerodock --help`, `zerodock dev --help` | Show available options |

With no subcommand, ZeroDock uses default startup with reload disabled.
`zerodock --reload` is not supported; the flag belongs to `dev`.

## Status and limitations

Functional handler reload is implemented in this checkout. Cross-runtime startup
and dispatch reliability remain under investigation. The approved baseline memory
limit is below 60 decimal MB of current server RSS; below 50MB remains an optimization
target. These are scoped baseline measurements, not promises for arbitrary handlers.

Read [Performance and validation](docs/performance.md) for exact boundaries, recorded
results, and environments that have not been tested.

## Documentation

- [Documentation index](docs/README.md)
- [Configuration reference](docs/configuration.md)
- [Handler, event, and response reference](docs/handlers.md)
- [Hot reload and debugging](docs/hot-reload.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [Architecture](docs/architecture.md)
- [Contributing](CONTRIBUTING.md)
- [Security considerations](docs/security.md)

## License

ZeroDock is released under the [MIT License](LICENSE).
