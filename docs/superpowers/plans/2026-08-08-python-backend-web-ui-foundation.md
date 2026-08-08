# Python Backend and Web UI Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Khởi tạo một monorepo chạy được với backend Python 3.14/FastAPI và website React/TypeScript, tách biệt mã nguồn UI và backend, có quy ước phát triển dành cho agent.

**Architecture:** Root repository chỉ điều phối công cụ và tài liệu; `backend/` là Python project độc lập theo Clean Architecture (domain, application, infrastructure, presentation), còn `ui/` là frontend project độc lập theo feature-based architecture. UI gọi backend qua HTTP contract `/api/v1/health`; dependency hướng vào domain, còn framework và adapter nằm ở biên ngoài để tuân thủ SOLID.

**Tech Stack:** uv, Python 3.14, FastAPI, Uvicorn, Pydantic Settings, Ruff, mypy, React, TypeScript, Vite, ESLint, npm.

## Global Constraints

- Python phải dùng chính xác version `3.14` và được quản lý bằng `uv`.
- Không tạo hoặc yêu cầu test tự động trong project.
- Code phải tuân thủ SOLID; domain và application không phụ thuộc FastAPI hay adapter hạ tầng.
- Mỗi function/method có logic nghiệp vụ phải có docstring hoặc comment giải thích **WHY** (lý do tồn tại, invariant hoặc quyết định thiết kế), không diễn giải **WHAT** mà câu lệnh đã thể hiện.
- Backend và UI phải có source code, dependency manifest và lệnh chạy riêng.
- Chỉ xây foundation và vertical slice health-check; không thêm database, authentication hoặc nghiệp vụ Information Retrieval khi chưa có yêu cầu.

---

## File Structure

```text
.
├── .gitignore                         # Loại trừ artifact của Python, Node và IDE
├── .python-version                    # Khóa Python 3.14 cho uv
├── AGENTS.md                          # Quy tắc chung và ranh giới backend/UI cho agent
├── Makefile                           # Lệnh điều phối setup, run và verify tại root
├── README.md                          # Hướng dẫn cài đặt và chạy toàn project
├── backend/
│   ├── pyproject.toml                 # Metadata, dependency và tool config Python
│   ├── uv.lock                        # Dependency lock do uv sinh
│   └── src/information_retrieval/
│       ├── __init__.py
│       ├── main.py                    # Composition root và FastAPI app factory
│       ├── domain/
│       │   ├── __init__.py
│       │   └── health.py              # Domain value object cho trạng thái dịch vụ
│       ├── application/
│       │   ├── __init__.py
│       │   ├── ports.py               # Protocol do application sở hữu
│       │   └── get_health.py           # Use case health-check
│       ├── infrastructure/
│       │   ├── __init__.py
│       │   ├── config.py              # Đọc environment bằng Pydantic Settings
│       │   └── system_health.py       # Adapter triển khai health port
│       └── presentation/http/
│           ├── __init__.py
│           ├── dependencies.py        # Dependency wiring cho HTTP layer
│           ├── schemas.py             # Response schema tại boundary HTTP
│           └── routes/health.py       # Endpoint `/api/v1/health`
└── ui/
    ├── .env.example                   # URL backend dùng bởi Vite
    ├── package.json                   # Script dev, lint, type-check và build
    ├── package-lock.json              # Dependency lock do npm sinh
    ├── index.html
    ├── tsconfig.json
    ├── tsconfig.app.json
    ├── tsconfig.node.json
    ├── vite.config.ts
    └── src/
        ├── main.tsx                   # Browser entrypoint
        ├── app/App.tsx                # Application shell
        ├── shared/api/http-client.ts  # HTTP boundary dùng chung
        ├── features/health/
        │   ├── api/get-health.ts      # Typed backend call
        │   ├── model/health.ts        # UI-facing contract
        │   └── ui/HealthStatus.tsx     # Feature component
        └── styles/global.css           # Global visual foundation
```

### Task 1: Root Tooling and Agent Guidance

**Files:**
- Create: `.python-version`
- Create: `.gitignore`
- Create: `AGENTS.md`
- Create: `Makefile`

**Interfaces:**
- Consumes: Không có.
- Produces: Python version contract `3.14`; root commands `setup`, `dev-backend`, `dev-ui`, `lint`, `typecheck`, `build`, `verify`; project-wide agent rules.

- [ ] **Step 1: Lock Python version and ignored artifacts**

Create `.python-version`:

```text
3.14
```

Create `.gitignore`:

```gitignore
# Python
__pycache__/
*.py[cod]
.mypy_cache/
.ruff_cache/
.venv/

# Node
ui/node_modules/
ui/dist/

# Environment and editors
.env
.env.*
!.env.example
.DS_Store
.idea/
.vscode/
```

- [ ] **Step 2: Add project instructions for coding agents**

Create `AGENTS.md` with this exact policy:

```markdown
# AGENTS.md

## Project boundaries

- Keep backend code in `backend/` and website code in `ui/`.
- In the backend, dependencies point inward: presentation and infrastructure may depend on application/domain; domain must not depend on frameworks.
- In the UI, feature-specific code stays under `src/features/<feature>`; only genuinely reusable code belongs in `src/shared`.

## Required engineering rules

- Do not create, generate, or require automated tests unless the user explicitly overrides this rule for a task.
- Apply SOLID: keep responsibilities narrow, depend on abstractions at boundaries, and extend behavior through focused components/adapters.
- Add a docstring or comment to every function or method containing business logic. Explain WHY the function, invariant, or design decision exists; never narrate WHAT the code visibly does.
- Do not add speculative abstractions, dependencies, database layers, or features without a current requirement.

## Tooling

- Use `uv` for Python installation, dependency management, locking, and command execution.
- The required Python version is 3.14.
- Run backend commands from `backend/` and UI commands from `ui/`, or use the root `Makefile`.
- Verification means lint, static type checking, build, and smoke checks. This repository intentionally has no automated test suite.
```

- [ ] **Step 3: Add root orchestration commands**

Create `Makefile`:

```makefile
.PHONY: setup dev-backend dev-ui lint typecheck build verify

setup:
	uv python install 3.14
	cd backend && uv sync
	cd ui && npm ci

dev-backend:
	cd backend && uv run uvicorn information_retrieval.main:create_app --factory --reload

dev-ui:
	cd ui && npm run dev

lint:
	cd backend && uv run ruff check .
	cd ui && npm run lint

typecheck:
	cd backend && uv run mypy src
	cd ui && npm run typecheck

build:
	cd ui && npm run build

verify: lint typecheck build
```

- [ ] **Step 4: Verify root contracts without installing dependencies**

Run:

```bash
test "$(cat .python-version)" = "3.14"
make -n setup dev-backend dev-ui verify
rg -n "Do not create|Apply SOLID|Explain WHY" AGENTS.md
```

Expected: version assertion succeeds, Make prints valid commands, and all three agent constraints are found.

- [ ] **Step 5: Commit root foundation**

```bash
git add .python-version .gitignore AGENTS.md Makefile
git commit -m "chore: define project foundation rules"
```

### Task 2: Backend Project and Configuration Boundary

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/src/information_retrieval/__init__.py`
- Create: `backend/src/information_retrieval/infrastructure/__init__.py`
- Create: `backend/src/information_retrieval/infrastructure/config.py`

**Interfaces:**
- Consumes: Python `3.14` contract from Task 1.
- Produces: immutable `Settings(app_name: str, environment: str, ui_origin: str)` and cached `get_settings() -> Settings`.

- [ ] **Step 1: Define the uv-managed backend project**

Create `backend/pyproject.toml`:

```toml
[project]
name = "information-retrieval-backend"
version = "0.1.0"
description = "Backend API for the Information Retrieval project"
requires-python = ">=3.14,<3.15"
dependencies = [
  "fastapi>=0.116,<1.0",
  "pydantic-settings>=2.10,<3.0",
  "uvicorn[standard]>=0.35,<1.0",
]

[dependency-groups]
dev = [
  "mypy>=1.17,<2.0",
  "ruff>=0.12,<1.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/information_retrieval"]

[tool.ruff]
target-version = "py314"
line-length = 100
src = ["src"]

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "SIM"]

[tool.mypy]
python_version = "3.14"
strict = true
files = ["src"]
```

- [ ] **Step 2: Add package markers**

Create empty files:

```text
backend/src/information_retrieval/__init__.py
backend/src/information_retrieval/infrastructure/__init__.py
```

- [ ] **Step 3: Implement typed environment configuration**

Create `backend/src/information_retrieval/infrastructure/config.py`:

```python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralize runtime policy so framework adapters do not read process state directly."""

    app_name: str = "Information Retrieval API"
    environment: str = "development"
    ui_origin: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_prefix="APP_", frozen=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Reuse one validated configuration to keep every adapter on the same runtime contract."""
    return Settings()
```

- [ ] **Step 4: Install and lock backend dependencies**

Run:

```bash
cd backend
uv python install 3.14
uv lock
uv sync
uv run python -c "import sys; assert sys.version_info[:2] == (3, 14)"
```

Expected: `backend/uv.lock` is created and the assertion exits successfully under Python 3.14.

- [ ] **Step 5: Verify backend configuration quality**

Run:

```bash
cd backend
uv run ruff check .
uv run mypy src
uv run python -c "from information_retrieval.infrastructure.config import get_settings; assert get_settings().environment == 'development'"
```

Expected: Ruff and mypy pass; the configuration smoke check exits successfully.

- [ ] **Step 6: Commit backend project setup**

```bash
git add backend/pyproject.toml backend/uv.lock backend/src
git commit -m "build: initialize uv backend project"
```

### Task 3: Backend Health Vertical Slice

**Files:**
- Create: `backend/src/information_retrieval/domain/__init__.py`
- Create: `backend/src/information_retrieval/domain/health.py`
- Create: `backend/src/information_retrieval/application/__init__.py`
- Create: `backend/src/information_retrieval/application/ports.py`
- Create: `backend/src/information_retrieval/application/get_health.py`
- Create: `backend/src/information_retrieval/infrastructure/system_health.py`
- Create: `backend/src/information_retrieval/presentation/__init__.py`
- Create: `backend/src/information_retrieval/presentation/http/__init__.py`
- Create: `backend/src/information_retrieval/presentation/http/routes/__init__.py`
- Create: `backend/src/information_retrieval/presentation/http/dependencies.py`
- Create: `backend/src/information_retrieval/presentation/http/schemas.py`
- Create: `backend/src/information_retrieval/presentation/http/routes/health.py`
- Create: `backend/src/information_retrieval/main.py`

**Interfaces:**
- Consumes: `Settings` and `get_settings()` from Task 2.
- Produces: `HealthStatus(status: str, service: str, environment: str)`, `HealthProbe.read() -> HealthStatus`, `GetHealth.execute() -> HealthStatus`, `create_app() -> FastAPI`, and JSON `GET /api/v1/health`.

- [ ] **Step 1: Define the framework-free domain value object**

Create package markers for `domain`, `application`, `presentation`, `presentation/http`, and `presentation/http/routes`, then create `domain/health.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HealthStatus:
    """Keep service readiness immutable so boundary adapters cannot corrupt probe results."""

    status: str
    service: str
    environment: str
```

- [ ] **Step 2: Define the application-owned port**

Create `application/ports.py`:

```python
from typing import Protocol

from information_retrieval.domain.health import HealthStatus


class HealthProbe(Protocol):
    """Invert the system-probe dependency so the use case remains independent of infrastructure."""

    def read(self) -> HealthStatus: ...
```

- [ ] **Step 3: Implement the health use case**

Create `application/get_health.py`:

```python
from information_retrieval.application.ports import HealthProbe
from information_retrieval.domain.health import HealthStatus


class GetHealth:
    def __init__(self, probe: HealthProbe) -> None:
        """Accept a port so alternate probes can be introduced without changing business flow."""
        self._probe = probe

    def execute(self) -> HealthStatus:
        """Expose one application operation shared by every future delivery mechanism."""
        return self._probe.read()
```

- [ ] **Step 4: Implement the infrastructure adapter**

Create `infrastructure/system_health.py`:

```python
from information_retrieval.domain.health import HealthStatus
from information_retrieval.infrastructure.config import Settings


class SystemHealthProbe:
    def __init__(self, settings: Settings) -> None:
        """Bind runtime metadata at composition time to keep probe output deterministic."""
        self._settings = settings

    def read(self) -> HealthStatus:
        """Report process readiness through the domain contract expected by the application."""
        return HealthStatus(
            status="ok",
            service=self._settings.app_name,
            environment=self._settings.environment,
        )
```

- [ ] **Step 5: Add the HTTP schema and dependency wiring**

Create `presentation/http/schemas.py`:

```python
from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    service: str
    environment: str
```

Create `presentation/http/dependencies.py`:

```python
from information_retrieval.application.get_health import GetHealth
from information_retrieval.infrastructure.config import get_settings
from information_retrieval.infrastructure.system_health import SystemHealthProbe


def get_health_use_case() -> GetHealth:
    """Keep concrete dependency construction at the HTTP edge instead of leaking it inward."""
    return GetHealth(SystemHealthProbe(get_settings()))
```

- [ ] **Step 6: Expose the versioned health endpoint**

Create `presentation/http/routes/health.py`:

```python
from typing import Annotated

from fastapi import APIRouter, Depends

from information_retrieval.application.get_health import GetHealth
from information_retrieval.presentation.http.dependencies import get_health_use_case
from information_retrieval.presentation.http.schemas import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
def read_health(
    use_case: Annotated[GetHealth, Depends(get_health_use_case)],
) -> HealthResponse:
    """Translate the application result at the HTTP boundary to preserve layer ownership."""
    health = use_case.execute()
    return HealthResponse(
        status=health.status,
        service=health.service,
        environment=health.environment,
    )
```

- [ ] **Step 7: Build the FastAPI composition root**

Create `main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from information_retrieval.infrastructure.config import get_settings
from information_retrieval.presentation.http.routes.health import router as health_router


def create_app() -> FastAPI:
    """Compose framework and adapters in one place so inner layers stay framework-agnostic."""
    settings = get_settings()
    app = FastAPI(title=settings.app_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.ui_origin],
        allow_credentials=True,
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    app.include_router(health_router, prefix="/api/v1")
    return app
```

- [ ] **Step 8: Verify static quality and the real HTTP contract**

Run terminal A:

```bash
cd backend
uv run ruff check .
uv run mypy src
uv run uvicorn information_retrieval.main:create_app --factory --host 127.0.0.1 --port 8000
```

Run terminal B after Uvicorn is ready:

```bash
curl --fail --silent http://127.0.0.1:8000/api/v1/health
```

Expected JSON:

```json
{"status":"ok","service":"Information Retrieval API","environment":"development"}
```

- [ ] **Step 9: Commit the backend vertical slice**

```bash
git add backend/src
git commit -m "feat: add backend health vertical slice"
```

### Task 4: UI Project and Health Feature

**Files:**
- Create: `ui/package.json`
- Create: `ui/package-lock.json`
- Create: `ui/.env.example`
- Create: `ui/index.html`
- Create: `ui/tsconfig.json`
- Create: `ui/tsconfig.app.json`
- Create: `ui/tsconfig.node.json`
- Create: `ui/vite.config.ts`
- Create: `ui/eslint.config.js`
- Create: `ui/src/vite-env.d.ts`
- Create: `ui/src/main.tsx`
- Create: `ui/src/app/App.tsx`
- Create: `ui/src/shared/api/http-client.ts`
- Create: `ui/src/features/health/model/health.ts`
- Create: `ui/src/features/health/api/get-health.ts`
- Create: `ui/src/features/health/ui/HealthStatus.tsx`
- Create: `ui/src/styles/global.css`

**Interfaces:**
- Consumes: backend `GET /api/v1/health` returning `{status, service, environment}` from Task 3.
- Produces: `requestJson<T>(path: string, init?: RequestInit) -> Promise<T>`, `getHealth() -> Promise<Health>`, and a browser UI showing loading, success, and failure states.

- [ ] **Step 1: Scaffold React TypeScript with Vite**

Run:

```bash
npm create vite@latest ui -- --template react-ts
cd ui
npm install
```

Expected: Vite creates TypeScript configuration, ESLint configuration, `package.json`, and `package-lock.json`. Keep current compatible package versions generated by the official scaffold instead of hand-pinning stale versions.

- [ ] **Step 2: Normalize UI scripts**

Ensure `ui/package.json` contains these scripts while preserving scaffolded dependencies:

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "lint": "eslint .",
    "typecheck": "tsc -b --pretty false",
    "preview": "vite preview"
  }
}
```

- [ ] **Step 3: Define the backend environment contract**

Create `ui/.env.example`:

```dotenv
VITE_API_BASE_URL=http://localhost:8000
```

Create or replace `ui/src/vite-env.d.ts`:

```typescript
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
```

- [ ] **Step 4: Add the shared HTTP boundary**

Create `ui/src/shared/api/http-client.ts`:

```typescript
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function requestJson<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  // WHY: One transport boundary keeps status validation consistent across features.
  const response = await fetch(`${API_BASE_URL}${path}`, init);

  if (!response.ok) {
    throw new Error(`API request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}
```

- [ ] **Step 5: Implement the typed health feature model and API**

Create `ui/src/features/health/model/health.ts`:

```typescript
export interface Health {
  status: string;
  service: string;
  environment: string;
}
```

Create `ui/src/features/health/api/get-health.ts`:

```typescript
import { requestJson } from "../../../shared/api/http-client";
import type { Health } from "../model/health";

export function getHealth(): Promise<Health> {
  // WHY: A feature-owned gateway prevents transport details from leaking into UI components.
  return requestJson<Health>("/api/v1/health");
}
```

- [ ] **Step 6: Implement loading, success, and failure UI states**

Create `ui/src/features/health/ui/HealthStatus.tsx`:

```tsx
import { useEffect, useState } from "react";

import { getHealth } from "../api/get-health";
import type { Health } from "../model/health";

type HealthState =
  | { kind: "loading" }
  | { kind: "ready"; health: Health }
  | { kind: "error"; message: string };

export function HealthStatus() {
  const [state, setState] = useState<HealthState>({ kind: "loading" });

  useEffect(() => {
    // WHY: Cancellation avoids committing a stale network result after the component unmounts.
    let active = true;

    void getHealth()
      .then((health) => {
        if (active) setState({ kind: "ready", health });
      })
      .catch((error: unknown) => {
        if (active) {
          const message = error instanceof Error ? error.message : "Unknown API error";
          setState({ kind: "error", message });
        }
      });

    return () => {
      active = false;
    };
  }, []);

  if (state.kind === "loading") return <p>Checking backend…</p>;
  if (state.kind === "error") return <p role="alert">Backend unavailable: {state.message}</p>;

  return (
    <dl className="health-card">
      <div><dt>Status</dt><dd>{state.health.status}</dd></div>
      <div><dt>Service</dt><dd>{state.health.service}</dd></div>
      <div><dt>Environment</dt><dd>{state.health.environment}</dd></div>
    </dl>
  );
}
```

- [ ] **Step 7: Compose the application shell**

Create `ui/src/app/App.tsx`:

```tsx
import { HealthStatus } from "../features/health/ui/HealthStatus";

export function App() {
  return (
    <main className="app-shell">
      <header>
        <p className="eyebrow">System foundation</p>
        <h1>Information Retrieval</h1>
        <p>Python backend and web UI are connected through a typed HTTP boundary.</p>
      </header>
      <section aria-labelledby="backend-status">
        <h2 id="backend-status">Backend status</h2>
        <HealthStatus />
      </section>
    </main>
  );
}
```

Replace `ui/src/main.tsx`:

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./app/App";
import "./styles/global.css";

const root = document.getElementById("root");

if (!root) {
  throw new Error("Root element is required to mount the application");
}

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
```

- [ ] **Step 8: Add a minimal responsive visual foundation**

Create `ui/src/styles/global.css`:

```css
:root {
  font-family: Inter, ui-sans-serif, system-ui, sans-serif;
  color: #172033;
  background: #f4f7fb;
  font-synthesis: none;
}

* { box-sizing: border-box; }
body { margin: 0; min-width: 320px; min-height: 100vh; }

.app-shell {
  width: min(720px, calc(100% - 2rem));
  margin: 0 auto;
  padding: 5rem 0;
}

.eyebrow { color: #3156d3; font-weight: 700; text-transform: uppercase; }
h1 { margin: 0; font-size: clamp(2.5rem, 8vw, 5rem); line-height: 1; }
section { margin-top: 3rem; }

.health-card {
  display: grid;
  gap: 1rem;
  padding: 1.5rem;
  border: 1px solid #dce3ef;
  border-radius: 1rem;
  background: #fff;
  box-shadow: 0 1rem 3rem rgb(23 32 51 / 8%);
}

.health-card div { display: flex; justify-content: space-between; gap: 1rem; }
.health-card dt { color: #667085; }
.health-card dd { margin: 0; font-weight: 700; }
```

- [ ] **Step 9: Verify UI static quality and production build**

Run:

```bash
cd ui
npm run lint
npm run typecheck
npm run build
```

Expected: all commands exit successfully and `ui/dist/index.html` exists.

- [ ] **Step 10: Commit the UI vertical slice**

```bash
git add ui
git commit -m "feat: add web UI health feature"
```

### Task 5: End-to-End Developer Guide and Smoke Verification

**Files:**
- Create: `README.md`

**Interfaces:**
- Consumes: root commands from Task 1, backend HTTP contract from Task 3, and UI feature from Task 4.
- Produces: reproducible local setup/run guide and verified browser-to-backend flow.

- [ ] **Step 1: Document setup, architecture, and commands**

Create `README.md`:

```markdown
# Information Retrieval

Monorepo gồm FastAPI backend chạy Python 3.14 và React website. Hai phần giữ dependency và source code riêng; root chỉ điều phối workflow.

## Prerequisites

- `uv`
- Node.js LTS và npm

## Setup

```bash
make setup
cp ui/.env.example ui/.env
```

## Run locally

Terminal 1:

```bash
make dev-backend
```

Terminal 2:

```bash
make dev-ui
```

Mở `http://localhost:5173`. API docs ở `http://localhost:8000/docs`; health endpoint ở `http://localhost:8000/api/v1/health`.

## Architecture

- `backend/domain`: model và invariant thuần Python.
- `backend/application`: use case và port do application sở hữu.
- `backend/infrastructure`: config và adapter triển khai port.
- `backend/presentation`: HTTP route, schema và dependency wiring.
- `ui/src/features`: code thuộc từng feature.
- `ui/src/shared`: primitive thật sự dùng chung giữa nhiều feature.

Dependency backend đi từ lớp ngoài vào lớp trong. UI component không gọi `fetch` trực tiếp mà đi qua feature API và shared HTTP boundary.

## Verification

```bash
make verify
```

Project chủ động không có automated tests theo quy ước trong `AGENTS.md`; verification gồm lint, type-check, production build và manual smoke check.
```

- [ ] **Step 2: Run the full static verification**

Run:

```bash
make verify
```

Expected: backend Ruff/mypy and UI ESLint/TypeScript/Vite build all succeed.

- [ ] **Step 3: Run the integrated browser smoke check**

Start backend and UI with `make dev-backend` and `make dev-ui`, then open `http://localhost:5173`.

Expected:

- Page title reads `Information Retrieval`.
- Backend status card changes from `Checking backend…` to `ok`.
- Service displays `Information Retrieval API`.
- Environment displays `development`.
- Browser console has no CORS or uncaught runtime errors.

- [ ] **Step 4: Commit the developer guide**

```bash
git add README.md
git commit -m "docs: add local development guide"
```

## Self-Review Result

- Spec coverage: Python 3.14/uv, separate backend/UI, popular layered patterns, no tests, SOLID, and WHY comments are each enforced by a concrete file and verification step.
- Placeholder scan: no deferred implementation markers or generic error-handling instructions remain.
- Interface consistency: UI `Health` matches backend `HealthResponse`; root commands match each project manifest; configuration names match CORS and runtime metadata consumers.
- Scope control: database, authentication, search/indexing, deployment, Docker, and CI are intentionally excluded because the request only establishes the project foundation.
