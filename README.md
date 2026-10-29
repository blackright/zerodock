# ⚡ ZeroDock

> **Run Python serverless functions locally without Docker, heavy containers, or cloud deploy delays.**

[![PyPI: zerodock](https://img.shields.io/pypi/v/zerodock.svg)](https://pypi.org/project/zerodock/)
[![CI: Status](https://github.com/blackright/zerodock/actions/workflows/ci.yml/badge.svg)](https://github.com/blackright/zerodock/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://www.python.org/)

---

## Why ZeroDock?

If you build serverless apps (like AWS Lambda, Google Cloud Functions, or Cloudflare Workers), testing them locally is usually frustrating:
1. **Cloud deploy loops:** You tweak one line of code, git push or run `sam deploy`, and wait 2 minutes just to see if your JSON parsed right.
2. **Heavy Docker emulators:** Tools like LocalStack or SAM CLI need Docker running, eat 2GB+ of RAM, and take 30+ seconds just to start up.

**ZeroDock takes a different approach:**
Instead of running an entire virtual machine or container, it runs your Python handlers directly on your machine using Python's native `importlib` and an ultra-fast async HTTP gateway (built on FastAPI and Uvicorn).

* ⚡ **Lightweight baseline:** current idle RSS must stay below **60MB** for the documented small workload; below **50MB** remains an optimization target. Engine startup targets <100ms, not a guaranteed whole-process readiness time.
* 📦 **No Docker required** — pure, native Python.
* 🐛 **Real breakpoints work** — drop `breakpoint()` into your handler and step through your code line by line in your terminal or IDE.
* 📄 **Simple declarative config** — one small YAML file defines all your routes and handlers.

---

## Quickstart (Under 2 Minutes)

### 1. Install ZeroDock

We recommend installing in a virtual environment:

```bash
# Create and activate a virtual environment (optional but recommended)
python -m venv .venv
# On Windows: .venv\Scripts\activate
# On macOS/Linux: source .venv/bin/activate

pip install zerodock
```

*(If you use `uv`: `uv add zerodock`)*

---

### 2. Create Your Config (`serverless-local.yaml`)

In your project root, create a file named `serverless-local.yaml`:

```yaml
version: "1.0"

gateway:
  host: "127.0.0.1"
  port: 8080

routes:
  api/hello:
    file: "./functions/hello.py"
    handler: "lambda_handler"
    methods: ["GET", "POST"]

  api/users:
    file: "./functions/users.py"
    handler: "handle_users"
    methods: ["GET"]
```

---

### 3. Write a Handler (`functions/hello.py`)

Create `functions/hello.py`:

```python
def lambda_handler(event, context):
    # Read query parameters (?name=Alice)
    params = event.get("queryStringParameters") or {}
    name = params.get("name", "World")

    # Read JSON body for POST requests
    body = event.get("body")

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": {
            "message": f"Hello, {name}!",
            "payload_received": body,
            "time_remaining_ms": context.get_remaining_time_in_millis()
        }
    }
```

---

### 4. Start the Gateway

```bash
zerodock dev
```

You'll see:
```text
INFO:     Started server process
INFO:     Uvicorn running on http://127.0.0.1:8080 (Press CTRL+C to quit)
```

---

### 5. Test Your Endpoint!

Open your browser or run:
```bash
curl "http://localhost:8080/api/hello?name=Developer"
```

Response:
```json
{
  "message": "Hello, Developer!",
  "payload_received": null,
  "time_remaining_ms": 30000
}
```

---

## CLI Reference

| Command / Flag | What it does | Default |
| :--- | :--- | :--- |
| `zerodock dev` | Start the local serverless HTTP gateway | Uses `serverless-local.yaml` |
| `zerodock dev --reload` | Watch configured handlers in the running gateway | Disabled by default |
| `-p`, `--port <PORT>` | Change the listening port | `8080` (or config file value) |
| `--host <HOST>` | Change the bind IP address | `127.0.0.1` |
| `-c`, `--config <PATH>` | Path to your configuration YAML file | `serverless-local.yaml` |
| `--log-level <LEVEL>` | Set verbosity (`debug`, `info`, `warning`, `error`) | `info` |
| `-v`, `--version` | Display installed ZeroDock version | — |
| `-h`, `--help` | Show complete command options | — |

**Pro Tip:** If the `zerodock` command isn't recognized directly in your terminal, you can always run:
```bash
python -m zerodock.cli dev
```

---

## Baseline Resource Budget

The approved memory acceptance limit is **<60,000,000 bytes current RSS** (decimal MB),
with **<50,000,000 bytes** retained as an optimization target. This applies to one
listening gateway with one GET route, one trivial handler file and config each no
larger than 1KiB, no extra handler dependencies, and no attached debugger/profiler.
Measure three fresh servers per reload mode: after the first valid response, idle
250ms and collect three current RSS samples 100ms apart; every sample must pass.
On Windows, measure the actual server PID's current working set, not peak or private
memory. Report runtime/dependency versions and platform with results; untested
environments are not covered by measurements on another runtime or OS.

Earlier Windows measurements were roughly 50-55MB with the tested runtimes, exceeding
the former 50MB gate. Those historical results are preserved. User handler imports,
larger route sets and other workloads may use more memory. The amended memory budget
does not waive dispatch, startup, quality or coverage requirements, and final feature
acceptance remains under review. The memory requirement was explicitly amended;
historical measurements are not retroactive passes under the old requirement.

## Hot Reload (Development)

```bash
zerodock dev --reload --config serverless-local.yaml
```

Save a configured handler, wait for its invalidation log, then request its route again. The next request executes fresh source without restarting the process or changing its port. No extra watcher package is needed. This flag belongs to `dev`; `zerodock --reload` is not supported.

The observer fingerprints only configured handler source paths, deduplicating shared files. It waits 100ms between scans. Detection within 500ms is the test target for small files on a normal local filesystem, not a promise for large projects, remote disks, or a blocked event loop.

Reload mode handles same-size/same-timestamp edits, atomic replacement, and deletion/recreation after startup. Invalid code returns the existing error response rather than an old successful result; save valid code to recover. An already-running invocation may finish using its old callable. Missing files at startup still fail configuration validation.

Both modes execute handler modules on every request; handler globals are not persistent application state. Without `--reload`, no observer starts and the existing loading path is preserved; this is not a promise that ordinary loading ignores edits.

Only configured handlers are refreshed. Imported helpers, installed packages, configuration changes, and new routes may require a restart. Native `breakpoint()` and source tracebacks remain available. Shutdown drains outstanding file reads before releasing watcher resources; a hung filesystem can delay shutdown indefinitely. No production multi-worker coordination is provided.

## Writing Handlers: The Event & Context Objects

ZeroDock handlers match the standard serverless function signature:
```python
def my_handler(event, context):
    ...
```
*(Both synchronous `def` and asynchronous `async def` handlers are fully supported!)*

### The `event` Object
The `event` dictionary provides incoming request data:
* `event["httpMethod"]` — HTTP method (`"GET"`, `"POST"`, `"PUT"`, `"DELETE"`, etc.).
* `event["path"]` — The URL path (e.g. `"/api/hello"`).
* `event["queryStringParameters"]` — Dictionary of URL query parameters (`{"name": "Alice"}`), or `None` if no query string was sent.
* `event["headers"]` — Dictionary of incoming HTTP headers (with lowercase keys for easy lookup).
* `event["body"]` — The parsed JSON dictionary if JSON was sent, or a raw string if plain text.

### The `context` Object
The `context` object supplies runtime execution metadata:
* `context.function_name` — Name of the handler being executed.
* `context.memory_limit_in_mb` — Memory limit in MB (default: `128`).
* `context.get_remaining_time_in_millis()` — Remaining time before request timeout (in milliseconds).

### What Your Handler Can Return
ZeroDock is designed to be developer-friendly. You can return responses in three ways:

1. **Standard Serverless Dict (Recommended):**
   ```python
   return {
       "statusCode": 200,
       "headers": {"Content-Type": "application/json"},
       "body": {"status": "success"}
   }
   ```
2. **Status Code and Body Tuple:**
   ```python
   return 201, {"id": "item_123", "created": True}
   ```
3. **Plain Dict or String (Auto-wrapped in HTTP 200):**
   ```python
   return {"status": "ok"}
   # or
   return "Hello from serverless!"
   ```

---

## Native Debugging: The Game Changer

Because ZeroDock runs your code directly on your computer's Python interpreter, you get **native host debugging**. No container attachments, no remote debugging proxies.

Just drop `breakpoint()` anywhere in your handler:
```python
def lambda_handler(event, context):
    name = event.get("queryStringParameters", {}).get("name")
    breakpoint()  # <-- Execution pauses right here!
    return {"statusCode": 200, "body": {"name": name}}
```
When you send an HTTP request, execution pauses instantly in your terminal with the interactive Python debugger (`pdb`). You can inspect variables, evaluate expressions, and step through line by line.

If you use VS Code or PyCharm, you can also set standard graphical red-dot breakpoints!

---

## 🛠️ Common Errors & Troubleshooting

Here are the most common things developers encounter and how to fix them in seconds:

### 1. `zerodock : The term 'zerodock' is not recognized...` (Windows)
* **Why it happens:** When you install packages globally on Windows (`pip install zerodock`), Python puts the `.exe` script into your user `Scripts` directory (e.g., `AppData\Local\...\Scripts`), which is often missing from your Windows `PATH`.
* **Fix 1 (Instant):** Run via Python directly:
  ```powershell
  python -m zerodock.cli dev
  ```
* **Fix 2 (Best Practice):** Use a virtual environment (`python -m venv .venv` and `.\.venv\Scripts\activate`). Virtual environments automatically add their `Scripts` folder to your PATH, so `zerodock dev` works everywhere.
* **Fix 3 (Permanent):** Add Python's Scripts folder to your User PATH in Windows Settings.

### 2. `Address already in use` or Port 8080 Conflict
* **Why it happens:** Another application (Docker, Tomcat, another web server) is already listening on port 8080.
* **The fix:** Tell ZeroDock to use a different port:
  ```bash
  zerodock dev --port 8081
  ```
  Or change the port in `serverless-local.yaml` under `gateway.port`.

### 3. `ConfigurationError: Could not find configuration file: serverless-local.yaml`
* **Why it happens:** You ran `zerodock dev` from a folder that doesn't contain your `serverless-local.yaml`.
* **The fix:** Either `cd` into the folder where `serverless-local.yaml` lives, or point to it explicitly:
  ```bash
  zerodock dev --config ./path/to/serverless-local.yaml
  ```

### 4. `HandlerLoadError: Handler file './functions/hello.py' not found`
* **Why it happens:** The file path inside `serverless-local.yaml` doesn't match where your `.py` file is stored relative to your working directory.
* **The fix:** Check the `file:` entry in your YAML file and verify that the file exists at that exact relative path.

### 5. `HandlerLoadError: Function 'lambda_handler' not found in module`
* **Why it happens:** The `handler:` name in `serverless-local.yaml` doesn't match the function name defined in your Python file.
* **The fix:** Check your `.py` file and make sure the function name matches `handler: "my_function_name"`.

### 6. Handlers Crashing with 500 Internal Server Error
* When your handler code has an unhandled exception (like a `KeyError` or `ValueError`), ZeroDock displays the full, colored Python traceback in your terminal and returns an HTTP 500 response with error details in the JSON body, keeping the gateway running without crashing.

👉 *For more in-depth solutions, platform quirks, and error walkthroughs, check our complete [TROUBLESHOOTING.md](TROUBLESHOOTING.md) guide.*

---

## 🗺️ Roadmap & What's Coming

ZeroDock is actively developed! Here is what is on the roadmap:
* **🔥 Handler hot reload:** Implemented locally with `zerodock dev --reload`; final performance and cross-platform acceptance remain under review.
* **🔐 Local Secrets & `.env` Loader (FEAT-008):** Automatically inject environment variables into your handlers from `.env` files.
* **☁️ Full Cloud Adapters (FEAT-005 - FEAT-007):** AWS Lambda full context emulation, Cloudflare Workers Fetch API, and Google Cloud Functions CloudEvents.
* **🗄️ Local Cloud Service Mocks (FEAT-009 - FEAT-012):** In-memory S3 bucket and DynamoDB/KV stores.

---

## 🤝 Contributing

We love contributions from developers of all experience levels! Please read our [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on setting up your local environment and submitting a Pull Request.

---

## 📄 License

ZeroDock is open-source software licensed under the [MIT License](LICENSE).
