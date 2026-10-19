# [FEAT-014] Rich Terminal UI (TUI) & Live Performance Monitor

**Labels**: `good first issue`, `help wanted`, `enhancement`, `cli-tui`

## 🎯 Task Summary
Make the ZeroDock startup and request logging gorgeous! Build a colorful terminal dashboard using the `rich` library that displays registered routes in a table, prints live color-coded HTTP status codes, and shows real-time handler execution latency.

## 💡 Background & Architecture
Developers love clear, beautiful CLI tools (like Vite, Next.js, and FastAPI). When `zerodock dev` starts, instead of plain uncolored text, it can display:
- A banner with version, host, and port.
- A clean markdown table of all registered HTTP routes, methods, and target files.
- Each incoming request formatted with color badges:
  - 🟢 `200 OK` in green with execution duration (e.g., `4.2ms`)
  - 🟡 `404 Not Found` in yellow
  - 🔴 `500 Server Error` in bold red

## 📋 Suggested Implementation Steps
1. Create `src/zerodock/cli_ui.py`:
   - Implement `render_startup_banner(config: GatewayConfig) -> None` using `rich.console.Console` and `rich.table.Table`.
   - Implement `render_request_log(method: str, path: str, status: int, duration_ms: float) -> None`.
2. Connect the UI logger to the FastAPI middleware in `src/zerodock/gateway/app.py`.
3. Add a `--no-color` or `--plain` flag in `cli.py` for headless CI environments.
4. Add unit test in `tests/unit/test_cli_ui.py`.

## ✅ Acceptance Criteria
- [ ] Registered routes are displayed in a formatted table on startup.
- [ ] Incoming requests log status codes and execution times in milliseconds with appropriate colors.
- [ ] Gracefully falls back to plain text if terminal does not support ANSI colors or when `--plain` is passed.
- [ ] Unit tests pass with `pytest`.
