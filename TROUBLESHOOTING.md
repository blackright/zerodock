# 🛠️ ZeroDock Troubleshooting & Diagnostic Guide

This guide covers common errors, platform-specific quirks (especially on Windows), and debugging tips to help you get unstuck in seconds.

---

## 📌 Quick Diagnosis Index

1. [Windows: `zerodock : The term 'zerodock' is not recognized`](#1-windows-zerodock--the-term-zerodock-is-not-recognized)
2. [Port Already in Use (`Errno 98` / `Errno 10048`)](#2-port-already-in-use-errno-98--errno-10048)
3. [`ConfigurationError: Could not find configuration file: serverless-local.yaml`](#3-configurationerror-could-not-find-configuration-file)
4. [`HandlerLoadError: Handler file './functions/...' not found`](#4-handlerloaderror-handler-file-not-found)
5. [`HandlerLoadError: Function '...' not found in module`](#5-handlerloaderror-function-not-found-in-module)
6. [Handler Returning 500 Internal Server Error](#6-handler-returning-500-internal-server-error)
7. [Debugging with Breakpoints](#7-debugging-with-breakpoints)
8. [JSON Serialization Errors in Handler Responses](#8-json-serialization-errors-in-handler-responses)

---

## 1. Windows: `zerodock : The term 'zerodock' is not recognized`

### The Problem
When installing packages globally via `pip install zerodock` in PowerShell or CMD on Windows, you might see this pip warning:
```text
WARNING: The script zerodock.exe is installed in 'C:\Users\<YourUser>\AppData\Local\...\Scripts' which is not on PATH.
```
And trying to run `zerodock` results in:
```text
zerodock : The term 'zerodock' is not recognized as the name of a cmdlet, function, script file, or operable program.
```

### Why it happens
Python installs `.exe` CLI wrapper tools into its user `Scripts` directory. If Windows doesn't have that directory in your `PATH` environment variable, PowerShell cannot find the command.

### The Solutions

#### Solution A: Run via Python Module (Works instantly everywhere)
You don't need to change any settings. Simply run:
```powershell
python -m zerodock.cli dev
```

#### Solution B: Use a Virtual Environment (Recommended Python Best Practice)
Virtual environments keep your computer clean and automatically register the `Scripts` folder in your active terminal:
```powershell
# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install and run
pip install zerodock
zerodock dev
```

#### Solution C: Add Python Scripts to your Windows PATH
To make `zerodock` work anywhere in any terminal window permanently:
1. Open PowerShell and run this one-liner:
   ```powershell
   [Environment]::SetEnvironmentVariable("Path", [Environment]::GetEnvironmentVariable("Path", "User") + ";$env:LOCALAPPDATA\Python\pythoncore-3.14-64\Scripts", "User")
   ```
2. Close and reopen your terminal.

---

## 2. Port Already in Use (`Errno 98` / `Errno 10048`)

### The Problem
```text
ERROR:    [Errno 10048] error while attempting to bind on address ('127.0.0.1', 8080): only one usage of each socket address is normally permitted
```

### Why it happens
Another process running on your machine (like Docker, an existing Python server, or another background service) is already listening on port `8080`.

### The Solution
You can override the port on the fly without touching your code:
```bash
zerodock dev --port 8081
```
Or update `serverless-local.yaml`:
```yaml
gateway:
  host: "127.0.0.1"
  port: 8081
```

---

## 3. `ConfigurationError: Could not find configuration file`

### The Problem
```text
zerodock.config.parser.ConfigurationError: Could not find configuration file: serverless-local.yaml
```

### Why it happens
ZeroDock looks for `serverless-local.yaml` in your **current working directory** (the folder where you ran the command).

### The Solution
* Either `cd` into the folder containing your YAML file:
  ```bash
  cd my-project
  zerodock dev
  ```
* Or pass the path directly with `--config`:
  ```bash
  zerodock dev --config ./configs/serverless-local.yaml
  ```

---

## 4. `HandlerLoadError: Handler file not found`

### The Problem
```text
zerodock.engine.loader.HandlerLoadError: Handler file './functions/my_handler.py' not found.
```

### Why it happens
The relative path specified in your `file:` entry doesn't exist relative to where you launched ZeroDock.

### The Solution
1. Verify the file exists.
2. Ensure the relative path in `serverless-local.yaml` matches:
   ```yaml
   routes:
     api/my-endpoint:
       file: "./functions/my_handler.py"   # <-- Check this path
       handler: "lambda_handler"
       methods: ["GET"]
   ```

---

## 5. `HandlerLoadError: Function not found in module`

### The Problem
```text
zerodock.engine.loader.HandlerLoadError: Function 'handle_request' not found in module './functions/api.py'.
```

### Why it happens
ZeroDock successfully found and imported your Python file, but the file doesn't contain a function named `handle_request`.

### The Solution
Open your Python file and make sure the function name matches your YAML config:
```python
# functions/api.py
def handle_request(event, context):   # <-- Name must match YAML 'handler:'
    return {"statusCode": 200, "body": {"ok": True}}
```

---

## 6. Handler Returning 500 Internal Server Error

### The Problem
Calling your endpoint returns:
```json
{
  "error": "InternalServerError",
  "message": "KeyError: 'user_id'",
  "type": "KeyError"
}
```

### Why it happens
Your function raised an uncaught Python exception. 

### How to diagnose
Look at your terminal where `zerodock dev` is running! ZeroDock prints the **full, unedited Python traceback** including the exact line number that crashed, just like running a normal Python script.

---

## 7. Debugging with Breakpoints

Because ZeroDock runs your code directly on your computer's native Python process, you don't need any complex remote debugging configurations.

### In Terminal (`pdb`)
Add `breakpoint()` anywhere in your code:
```python
def lambda_handler(event, context):
    user_id = event.get("queryStringParameters", {}).get("id")
    breakpoint()  # Execution will halt right here!
    return {"statusCode": 200, "body": {"user": user_id}}
```
When you make an HTTP request to this endpoint, your terminal will immediately halt and present you with the interactive Python debugger prompt (`(Pdb)`).

### In VS Code
1. Open your project in VS Code.
2. Click to the left of any line number in your handler file to set a standard red breakpoint dot.
3. In VS Code's Run & Debug tab, run `Python Debugger: Current File` or attach to process.

---

## 8. JSON Serialization Errors in Handler Responses

### The Problem
```text
TypeError: Object of type datetime is not JSON serializable
```

### Why it happens
Standard JSON does not natively support non-primitive Python types like `datetime`, `UUID`, or custom classes.

### The Solution
Convert them to strings or ISO formats before returning:
```python
from datetime import datetime

def lambda_handler(event, context):
    return {
        "statusCode": 200,
        "body": {
            "timestamp": datetime.utcnow().isoformat()  # <-- String format
        }
    }
```

---

## 💬 Still Stuck?

If you run into an issue that isn't listed here, we're here to help:
* Open an issue or discussion on our GitHub repo: [https://github.com/blackright/zerodock/issues](https://github.com/blackright/zerodock/issues)
* Include your `serverless-local.yaml` and the terminal error output.
