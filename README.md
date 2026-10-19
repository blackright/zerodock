# ⚡ ZeroDock

> **Run serverless functions locally without Docker, heavy containers, or cloud deploy delays. Pure Python, sub-100ms startup.**

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

* ⚡ **Starts in <100ms** and uses less than 50MB of RAM.
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
* **🔥 Hot-Reloading File Watcher (Sprint 2):** Automatically reload handlers when you save `.py` files without restarting the server.
* **🔐 Local Secrets & `.env` Loader (FEAT-008):** Automatically inject environment variables into your handlers from `.env` files.
* **☁️ Full Cloud Adapters (FEAT-005 - FEAT-007):** AWS Lambda full context emulation, Cloudflare Workers Fetch API, and Google Cloud Functions CloudEvents.
* **🗄️ Local Cloud Service Mocks (FEAT-009 - FEAT-012):** In-memory S3 bucket and DynamoDB/KV stores.

---

## 🤝 Contributing

We love contributions from developers of all experience levels! Please read our [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on setting up your local environment and submitting a Pull Request.

---

## 📄 License

ZeroDock is open-source software licensed under the [MIT License](LICENSE).
