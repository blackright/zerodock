# [FEAT-008] Local Environment & Secrets Loader (.env.local)

**Labels**: `good first issue`, `help wanted`, `enhancement`, `developer-experience`

## 🎯 Task Summary
Implement automatic parsing and injection of local environment variables and secrets from `.env.local` or `.env` files into the function runtime environment, keeping secrets safe from git commits.

## 💡 Background & Architecture
In production, cloud functions access secrets via AWS Secrets Manager, SSM Parameter Store, or cloud environment variables. Locally, developers store their API keys and test database passwords in `.env.local` files.
ZeroDock should:
1. Automatically look for `.env.local` or `.env` files in the workspace root.
2. Safely parse them without overriding already-set system environment variables (unless configured).
3. Inject the values into `os.environ` or the `event["stageVariables"]` payload before invoking the function handler.

## 📋 Suggested Implementation Steps
1. Create `src/zerodock/config/secrets.py`:
   - Implement `load_local_env(env_file_path: Path | None = None) -> dict[str, str]`:
     - Reads key-value pairs (ignoring comments `#` and blank lines).
     - Returns parsed dictionary.
2. In `src/zerodock/engine/context.py`, ensure loaded secrets are accessible via `InvocationContext.client_context` or stage variables.
3. Add `.env.local` and `.env` to `.gitignore` (already done).
4. Add unit test in `tests/unit/test_secrets_loader.py` validating that keys are correctly parsed and loaded.

## ✅ Acceptance Criteria
- [ ] `.env.local` file is loaded at startup if present.
- [ ] Serverless handlers can access variables via `os.environ` or context.
- [ ] No crash if `.env.local` file does not exist (graceful fallback).
- [ ] Unit tests pass with `pytest`.
