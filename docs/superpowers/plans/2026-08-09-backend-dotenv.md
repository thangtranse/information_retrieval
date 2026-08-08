# Backend `.env` Configuration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cho phép backend tự động đọc cấu hình development từ `backend/.env` thông qua một file mẫu an toàn được commit.

**Architecture:** `Settings` tiếp tục là boundary duy nhất đọc cấu hình runtime bằng Pydantic Settings. `backend/.env.example` định nghĩa contract được chia sẻ, `backend/.env` chứa giá trị local và bị Git ignore; biến môi trường hệ thống vẫn có thể ghi đè file dotenv theo precedence chuẩn của Pydantic.

**Tech Stack:** Python 3.14, uv, Pydantic Settings, Ruff, mypy.

## Global Constraints

- Không commit secret hoặc `backend/.env`.
- Không thêm dependency; `pydantic-settings` hiện có đảm nhận việc đọc dotenv.
- Không thêm automated tests theo `AGENTS.md`.
- Giữ Python 3.14 và workflow `uv` hiện tại.
- Docstring/comment chỉ giải thích WHY, không mô tả WHAT.
- Chỉ thêm ba biến `APP_NAME`, `APP_ENVIRONMENT`, và `APP_UI_ORIGIN`; không thêm production secret management hoặc environment-specific dotenv files.

---

## File Structure

```text
backend/
├── .env                              # Local development values; ignored, never committed
├── .env.example                      # Committed backend configuration contract
└── src/information_retrieval/
    └── infrastructure/config.py      # Pydantic Settings dotenv loading policy
README.md                             # Setup instructions for backend and UI env files
```

### Task 1: Backend Dotenv Contract and Runtime Loading

**Files:**
- Create: `backend/.env.example`
- Create locally, do not stage: `backend/.env`
- Modify: `backend/src/information_retrieval/infrastructure/config.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: existing `Settings(app_name: str, environment: str, ui_origin: str)` and `get_settings() -> Settings`.
- Produces: dotenv keys `APP_NAME`, `APP_ENVIRONMENT`, `APP_UI_ORIGIN`; automatic loading from `backend/.env` when backend commands run from `backend/`.

- [ ] **Step 1: Add the committed backend environment contract**

Create `backend/.env.example`:

```dotenv
APP_NAME=Information Retrieval API
APP_ENVIRONMENT=development
APP_UI_ORIGIN=http://localhost:5173
```

- [ ] **Step 2: Configure Pydantic Settings to load dotenv**

Replace the `model_config` declaration in `backend/src/information_retrieval/infrastructure/config.py` with:

```python
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="APP_",
        frozen=True,
    )
```

Do not change the current fields, defaults, cache behavior, imports, or WHY-oriented docstrings.

- [ ] **Step 3: Create the ignored local backend configuration**

Run from the repository root:

```bash
cp backend/.env.example backend/.env
git check-ignore --quiet backend/.env
```

Expected: `backend/.env` exists and `git check-ignore` exits `0`. Never run `git add -f backend/.env`.

- [ ] **Step 4: Document backend and UI environment setup**

Replace the README setup block:

```bash
make setup
cp ui/.env.example ui/.env
```

with:

```bash
make setup
cp backend/.env.example backend/.env
cp ui/.env.example ui/.env
```

Add this sentence immediately after the block:

```markdown
Hai file `.env` chỉ dùng local và không được commit; thay đổi giá trị `APP_*` trong `backend/.env` khi cần cấu hình backend development.
```

- [ ] **Step 5: Verify backend static quality**

Run:

```bash
cd backend
uv run ruff check .
uv run mypy src
```

Expected: Ruff prints `All checks passed!`; mypy prints `Success: no issues found`.

- [ ] **Step 6: Verify dotenv parsing and environment precedence**

Run from `backend/`:

```bash
uv run python -c 'from information_retrieval.infrastructure.config import get_settings; get_settings.cache_clear(); s = get_settings(); assert s.app_name == "Information Retrieval API"; assert s.environment == "development"; assert s.ui_origin == "http://localhost:5173"'
APP_ENVIRONMENT=verification uv run python -c 'from information_retrieval.infrastructure.config import Settings; assert Settings().environment == "verification"'
```

Expected: both commands exit `0`. The first proves the local file is parsed; the second proves a process environment variable overrides the dotenv value.

- [ ] **Step 7: Verify the Git safety boundary**

Run from the repository root:

```bash
git check-ignore -v backend/.env
git status --short
git diff --check
```

Expected:

- `git check-ignore` identifies the existing `.env` ignore rule.
- `backend/.env` is absent from `git status`.
- Only `backend/.env.example`, `config.py`, `README.md`, and this plan appear as tracked work for the implementation; the already committed design spec remains unchanged.
- `git diff --check` produces no output.

- [ ] **Step 8: Commit the dotenv implementation**

```bash
git add backend/.env.example backend/src/information_retrieval/infrastructure/config.py README.md docs/superpowers/plans/2026-08-09-backend-dotenv.md
git commit -m "feat: add backend dotenv configuration"
```

Do not stage `backend/.env`.

## Self-Review Result

- Spec coverage: committed example, ignored local file, runtime dotenv loading, environment override precedence, documentation, and Git safety checks are all covered.
- Placeholder scan: no deferred or ambiguous implementation steps remain.
- Type consistency: dotenv keys map through `env_prefix="APP_"` to the existing fields `app_name`, `environment`, and `ui_origin` without changing their public interface.
- Scope control: no new dependencies, tests, secrets, deployment configuration, database settings, or environment variants are introduced.
