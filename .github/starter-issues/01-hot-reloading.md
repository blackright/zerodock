# [FEAT-002] Hot-Reloading & Dynamic Module Cache Invalidation

**Labels**: `good first issue`, `help wanted`, `enhancement`, `core-engine`

## 🎯 Task Summary
Currently, when a developer modifies their Python serverless handler in `functions/hello.py`, they must restart the ZeroDock server to test their changes. We want to implement **instant hot-reloading** so that saving any handler file automatically invalidates Python's internal `sys.modules` cache and picks up the fresh code on the very next HTTP request!

## 💡 Background & Architecture
ZeroDock uses Python's `importlib.util` in `src/zerodock/engine/loader.py` to dynamically load handler files at runtime.
When a file changes:
1. A file watcher detects the file write event.
2. The engine deletes the module name from `sys.modules`.
3. The next invocation in `loader.py` loads the fresh code without restarting the server.

## 📋 Suggested Implementation Steps
1. Add an optional file watcher (e.g., using `watchfiles` or standard asynchronous file polling).
2. In `src/zerodock/engine/loader.py`, add a function `invalidate_handler_cache(module_name: str) -> None`:
   ```python
   import sys
   if module_name in sys.modules:
       del sys.modules[module_name]
   ```
3. Add a `--reload` flag in `src/zerodock/cli.py` to enable file watching in development mode.
4. Add unit test in `tests/unit/test_loader.py` demonstrating that updating file contents on disk updates the handler output after calling `invalidate_handler_cache()`.

## ✅ Acceptance Criteria
- [ ] Saving a handler file updates its response on the next HTTP request without restarting the gateway.
- [ ] No regression on sub-100ms startup or latency benchmarks.
- [ ] Unit and integration tests pass with `pytest`.
