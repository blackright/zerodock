# Contributing to ZeroDock

Thank you for your interest in contributing to **ZeroDock**! 

ZeroDock is built by developers, for developers. Our architecture is explicitly designed so you can contribute an isolated feature (like a new cloud event transformer or local mock) without needing to understand the entire engine.

---

## 🧭 Code of Conduct

We are committed to providing a friendly, welcoming, and inclusive environment for everyone. Please treat all community members with respect and kindness.

---

## 🛠️ Local Development Setup

### 1. Prerequisites
- Python 3.10 or higher
- Git

### 2. Fork and Clone
```bash
git clone https://github.com/your-username/zerodock.git
cd zerodock
```

### 3. Set Up Your Environment
Create a virtual environment and install development dependencies:
```bash
python -m venv .venv

# On Linux/macOS:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate

pip install -e ".[dev]"
```

### 4. Run the Test Suite
Tests must pass before submitting a Pull Request:
```bash
pytest
```

---

## 🎯 How to Contribute

### Finding Good First Issues
Check our [GitHub Issues](https://github.com/blackright/zerodock/issues) tracker. Look for tickets tagged with:
- `good first issue`: Self-contained tasks perfect for new contributors.
- `help wanted`: Features or enhancements ready to be claimed.

### Proposing a New Feature
1. Open an issue with the label `feature-proposal`.
2. Briefly describe the problem, proposed solution, and sample `serverless-local.yaml` usage.
3. Wait for feedback from maintainers before writing a major PR.

---

## 📋 Architectural Guidelines

ZeroDock follows strict constitutional principles:
1. **Speed & Featherweight Footprint**: The engine MUST boot in <100ms and keep baseline actual listening-server idle RSS below 60 decimal MB (60,000,000 bytes); <50MB remains an optimization target. Follow the constitution's one-route/small-handler workload, three fresh processes per reload mode, and current-RSS sampling protocol. Report the tested environment; do not promise the baseline limit for arbitrary handler imports. Do not introduce heavy background daemons or Docker dependencies.
2. **Native Execution**: Code runs directly in Python via `importlib`. Breakpoints (`breakpoint()`) must always work.
3. **Decoupled Plugins**: Event transformers and mock services should be isolated modules in `src/zerodock/` with standalone tests.
4. **Test-Driven Quality**: Every new feature must include unit tests and authentic payload fixtures in `tests/`.

---

## 🚀 Submitting a Pull Request (PR)

1. Create a feature branch: `git checkout -b feat/my-new-feature`
2. Write clean, readable code with type hints.
3. Ensure all tests pass: `pytest`
4. Format code using `ruff`: `ruff check . --fix`
5. Commit your changes: `git commit -m "feat: add S3 event transformer"`
6. Push to your fork and open a Pull Request.

---

## 📦 Release & Publishing Workflow (For Maintainers)

ZeroDock uses **PyPI Trusted Publishing** via OpenID Connect (OIDC). Releases are 100% automated via GitHub Actions:

### 1. One-Time PyPI Configuration
1. In [pypi.org](https://pypi.org) ➔ Account Settings ➔ **Publishing**.
2. Add GitHub Publisher:
   - Owner: `blackright`
   - Repository: `zerodock`
   - Workflow name: `publish.yml`
   - Environment: `pypi`

### 2. Making an Official Release
1. Bump version in `pyproject.toml` (e.g., `0.1.0` ➔ `0.1.1`).
2. Commit and push to `main`.
3. Create and push a Git release tag:
   ```bash
   git tag v0.1.1
   git push origin v0.1.1
   ```
4. GitHub Actions automatically builds the wheel, runs multi-OS smoke tests, and publishes directly to PyPI!

---

## 💬 Getting Help
If you get stuck or have questions, feel free to open a Discussion on GitHub or comment directly on the issue you're working on. We're happy to guide you!
