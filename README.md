# ⚡ ZeroDock

> **Zero-dependency, ultra-lightweight local execution engine that simulates serverless cloud architectures at the application layer using native asynchronous Python.**

[![PyPI: zerodock](https://img.shields.io/pypi/v/zerodock.svg)](https://pypi.org/project/zerodock/)
[![CI: Status](https://github.com/blackright/zerodock/actions/workflows/ci.yml/badge.svg)](https://github.com/blackright/zerodock/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://www.python.org/)
[![Startup: <100ms](https://img.shields.io/badge/Startup-%3C100ms-success.svg)](#)
[![RAM: <50MB](https://img.shields.io/badge/RAM-%3C50MB-success.svg)](#)

---

## 🚨 The Problem

Modern cloud development leans heavily on **Serverless Architectures** (such as AWS Lambda, Google Cloud Functions, and Cloudflare Workers) because they scale effortlessly and cost nothing when idle. However, the local development experience for these platforms is fundamentally broken.

To test a simple serverless function locally before deploying it to production, developers are traditionally forced into two bad options:
1. **Deploying directly to the cloud to test:** This adds a 30-second to 3-minute feedback loop for every minor typo or code tweak.
2. **Running heavy local emulation suites:** Tools like LocalStack, AWS SAM, or multi-container Docker setups mimic entire cloud infrastructure stacks.

These existing solutions introduce massive friction into a developer's daily workflow: **massive resource bloat** (hogging 2GB+ of RAM), **sluggish startup times**, a **"black box" debugging nightmare**, and a **high barrier to entry** for contributors who just want to run a function locally.

---

## 💡 The Solution

Instead of simulating the cloud at the *infrastructure layer* using virtual machines and containers, **ZeroDock** simulates the cloud at the *application layer* using native, asynchronous Python. 

It acts as a **"Docker-Compose without Docker"** tailored specifically for serverless handlers. 

*   ⚡ **Featherweight & Instant:** Built on native `asyncio` and `FastAPI`, it boots up in under 100 milliseconds and uses less than 50MB of RAM.
*   📦 **Containerless Isolation:** Leverages Python’s built-in `importlib` and `sys.modules` manipulation to dynamically inject event data, run the handler function, and keep the execution context clean.
*   🐛 **Native Debugging Integration:** Because code runs natively on your host machine's Python runtime, you can set standard breakpoints (`breakpoint()` or a red dot in VS Code) anywhere in your serverless code and step through line by line instantly.
*   📄 **Declarative Infrastructure:** Define your API endpoints, routing paths, and target Python files in a single, human-readable `serverless-local.yaml` file.

---

## 🚀 Quick Start

### 📦 1. Installation via pip (Recommended)

Install ZeroDock directly from PyPI into your active virtual environment:
```bash
pip install zerodock
```
*(Or if using `uv`)*:
```bash
uv add zerodock
```

---

### 💻 2. Installing from Source (For Contributors)

Clone the repository and install dependencies:
```bash
git clone https://github.com/blackright/zerodock.git
cd zerodock
pip install -e ".[dev]"
```
*(Or if using `uv`)*:
```bash
uv sync
```

### 3. Define Your Infrastructure (`serverless-local.yaml`)
Create a configuration file in your project root to map routes to your local Python serverless files:
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
```

### 4. Create a Sample Handler (`functions/hello.py`)
```python
def lambda_handler(event, context):
    name = event.get("queryStringParameters", {}).get("name", "World")
    return {
        "statusCode": 200,
        "body": {"message": f"Hello, {name}! Sent natively from ZeroDock."}
    }
```

### 5. Run the Simulator
Start the ZeroDock local gateway:
```bash
python -m zerodock.cli dev
# or
uvicorn zerodock.gateway.app:app --port 8080
```

Your mock serverless API gateway is now running at `http://localhost:8080`.

Test your endpoint:
```bash
curl "http://localhost:8080/api/hello?name=OpenSource"
```

---

## 🗺️ Feature Roadmap & Wishlist

We welcome contributions! These roadmap features are explicitly designed so community developers can jump in:

### ⚙️ Core Engine & Performance
*   **Hot-Reloading File Watcher:** Background file watcher that automatically clears the `sys.modules` cache when a function file is saved, enabling real-time code updates without restarting the gateway.
*   **Dynamic Middleware Pipeline:** Execute pre-handler and post-handler logic mimicking cloud middleware (e.g., AWS Lambda Layers or Cloudflare Advanced Routing).
*   **Multi-Language Execution Layers:** Lightweight bindings (like Node.js via subprocess or Pyodide) to simulate JavaScript/TypeScript handlers alongside Python functions.

### 🌐 Cloud Platform Contexts
*   **AWS Lambda Payload Wrapper:** Transformer that formats incoming HTTP requests into valid AWS Lambda `event` and `context` schemas (including Cognito auth contexts).
*   **Cloudflare Workers Runtime Wrapper:** Environment injector that mimics the `env`, `ctx`, and Fetch API behavior specific to Cloudflare Workers.
*   **Google Cloud Functions Event Mocks:** Support for CloudEvent formats used by GCP functions.

### 🔌 Simulated Cloud Integration Plugins (The "Mock" Ecosystem)
*   **Local Secret & Env Loader:** Read and inject `.env` files dynamically based on active routes, simulating cloud environment variable configurations.
*   **Mock Key-Value (KV) Store:** Simple, memory-based or SQLite-backed local Key-Value storage engine mimicking Cloudflare KV or AWS DynamoDB.
*   **Mock Object Storage:** Directory-backed local S3 bucket simulation.
*   **Cron & Scheduled Trigger Simulator:** Internal loop system that reads `cron:` syntax from `serverless-local.yaml` and executes functions at designated intervals.
*   **Mock Pub/Sub Queue Event Bus:** In-memory queue system to simulate message broker events triggering functions asynchronously (like AWS SQS or GCP Pub/Sub).

---

## 🤝 Contributing

We love contributions! Please read our [CONTRIBUTING.md](CONTRIBUTING.md) for full guidelines on code standards, local development, and how to submit a Pull Request.

---

## 📄 License

This project is open-source software licensed under the [MIT License](LICENSE).
