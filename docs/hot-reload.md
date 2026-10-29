# Hot Reload and Debugging

Hot reload keeps the gateway running while configured handler source changes.
It is opt-in and uses the same process and listening port.

## Enable reload

```bash
python -m zerodock.cli dev --reload --config serverless-local.yaml
```

If the flag is not present in `dev --help`, check your installation against the
[release-status guidance](../README.md#installation-and-release-status).
`--reload` belongs to `dev`, not the top-level command or YAML configuration.

## Save visibility

1. Save a configured handler file.
2. Wait for its invalidation log.
3. Make the next request to its route.

After a completed stable save is detected and invalidated, the next request loads
fresh source. An earlier request may already see the change because handlers still
execute per request. Requests racing a partial write may fail, and invocations
already holding a callable may finish with the older version.

The observer reads content fingerprints for exact configured paths and waits 100ms
between scans. Detection within 500ms is the test target for a documented small
local workload, not a guarantee under arbitrary file sizes, remote disks, or a
blocked event loop. Shared source paths are deduplicated within an application.

## Recovery and scope

Same-size/same-timestamp edits and atomic file replacement are covered. Invalid
source returns the existing error response, not a cached successful response.
After startup, deletion/recreation or a corrected save can recover automatically.
Missing handler files still fail initial configuration validation.

Only configured handler files are observed. Restart for imported-helper or dependency
changes, YAML updates, new routes, or changed runtime settings. There is no dependency
graph reload, persistent callable cache, global-state migration, or production
multi-worker coordination protocol.

Without `--reload`, no observer starts and the original loading path remains.
This does not mean ordinary loading ignores all edits; it means bytecode-independent
freshness and observation guarantees apply to reload-enabled loading.

## Shutdown

Observation starts and stops with application lifespan. Shutdown signals stop,
drains outstanding file reads, and releases app-owned registrations without shutting
down a shared executor. A paused debugger or hung filesystem can delay completion;
cancelling an await is not proof that a worker's filesystem operation ended.

## Debugging

### Terminal debugger

Use a safe query-parameter lookup before pausing:

```python
def lambda_handler(event, context):
    parameters = event.get("queryStringParameters") or {}
    name = parameters.get("name", "World")
    breakpoint()
    return {"message": f"Hello, {name}!"}
```

Run the gateway in an interactive terminal and send a request. At the debugger
prompt, inspect `event` or `name`, then use `continue` to finish the request.
Your environment's `PYTHONBREAKPOINT` setting can change or disable this behavior.
Ctrl+C can be handled by the debugger after continuing; finish the debugging session
before expecting normal server shutdown. See the [Python debugger reference](https://docs.python.org/3/library/pdb.html).

### IDE debugging

Start the gateway under the IDE debugger with the correct environment selected.
Opening a handler and setting a visual breakpoint does not attach a debugger to
an existing server process.

The repository provides a VS Code launch configuration in `.vscode/launch.json`.
Select the intended interpreter, then choose the ZeroDock gateway configuration.
Its current arguments start `dev` without reload; add `--reload` in your reviewed
launch configuration when needed. Ensure its working directory contains the config
or pass `--config` explicitly. See [VS Code Python debugging](https://code.visualstudio.com/docs/python/debugging).

Controlled native source/stack/continue checks have been exercised. A complete
GUI/IDE validation matrix has not been run; no IDE-specific result is implied.
