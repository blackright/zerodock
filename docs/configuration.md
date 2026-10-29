# Configuration Reference

ZeroDock reads `serverless-local.yaml` by default. Use `dev --config PATH` to select
another YAML file. The configuration describes a gateway and at least one route.

## Complete example

Create the referenced `functions/hello.py` before starting the gateway:

```yaml
version: "1.0"
gateway:
  host: "127.0.0.1"
  port: 8080
  log_level: "info"
routes:
  /api/hello:
    file: "./functions/hello.py"
    handler: "lambda_handler"
    methods: ["GET", "POST"]
    timeout_seconds: 30
```

The [README example](../README.md#quickstart) provides a matching handler.

## Top-level fields

| Field | Required | Default | Meaning |
| --- | --- | --- | --- |
| `version` | No | `"1.0"` | Configuration version string; not the package version |
| `gateway` | No | Defaults below | Bind address, port, and logging |
| `routes` | Yes | None | Non-empty mapping from HTTP paths to handlers |

## Gateway fields

| Field | Default | Constraints |
| --- | --- | --- |
| `host` | `127.0.0.1` | Bind address; keep loopback for local use |
| `port` | `8080` | Integer from 1024 through 65535 |
| `log_level` | `info` | `debug`, `info`, `warning`, or `error` |

The CLI's `--host`, `--port`, and `--log-level` override their configured values.
Do not bind a development server to an external interface without understanding
[its security limitations](security.md).

## Route fields

| Field | Required | Default | Constraints |
| --- | --- | --- | --- |
| `file` | Yes | None | Existing Python source path |
| `handler` | No | `handler` | Callable name; must be a valid identifier |
| `methods` | No | All supported methods | List of supported HTTP methods |
| `timeout_seconds` | No | `30` | Integer from 1 through 900 |

Supported methods are `GET`, `POST`, `PUT`, `DELETE`, `PATCH`, `HEAD`, and `OPTIONS`.
Specify the methods you intend to expose rather than relying on the broad default.
The timeout applies to awaited asynchronous execution; it cannot forcibly interrupt
blocking synchronous code. See [execution limits](handlers.md#execution-limits).

Route names are normalized to include a leading slash and remove a trailing slash
except for `/`. Treat them as configured HTTP paths, not filesystem patterns.

## Path resolution and validation

Relative handler paths are resolved against the configuration file's directory.
For example, `configs/local.yaml` containing `file: "../functions/hello.py"` targets
the sibling `functions` directory regardless of the command's working directory.

The parser checks YAML structure, field validation, and handler-file existence at
startup. Source import errors and missing/non-callable entrypoints are reported when
the handler is loaded for a request. Reload does not defer initial file-existence
validation.

## Changes that require a restart

Reload watches configured handler source files, not YAML. Restart after changing
routes, configuration, bind settings, or callable names in the configuration.
There is no YAML `reload` field; enable observation with `dev --reload`.

Storage mocks, automatic `.env` loading, cloud-adapter selection, and scaffolding
configuration are not implemented settings. A roadmap proposal is not an available
configuration option.
