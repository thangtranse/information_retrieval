# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

`AGENTS.md` holds the binding engineering rules for this repo; read it first. This file adds workflow and architecture context and must not contradict it.

## Superpowers workflow (mandatory)

This project is driven by Superpowers plans and specs. All work is anchored in `docs/superpowers/`:

- `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md` — the design/contract for a change.
- `docs/superpowers/plans/YYYY-MM-DD-<topic>.md` — the checkbox (`- [ ]`) implementation plan derived from a spec.

Rules:

- Only implement work that is described by a spec and plan under `docs/superpowers/`. If a request has no matching document, write/extend the spec (and then the plan) first, get it approved, and only then write code.
- Execute plans task-by-task via the Superpowers execution skills referenced in the plan header (`superpowers:subagent-driven-development` or `superpowers:executing-plans`), and keep checkboxes updated as tasks complete.
- Never silently widen scope beyond a plan's "In scope"; out-of-scope items go back into a new spec.
- New documents follow the existing filename date prefix and the existing section shape (Goal / Scope with In-and-Out / Architecture; plans use Goal / Architecture / Tech Stack / Global Constraints / File Structure / checkbox tasks).
- Documents are written in the same mixed Vietnamese-with-English-technical-terms style as the existing ones.

## Commands

Run from repo root:

```bash
make setup        # uv python 3.14 + backend uv sync + ui npm ci
```

```bash
make dev-backend  # uvicorn --reload on :8000
```

```bash
make dev-ui       # vite on :5173
```

```bash
make format       # ruff format + prettier (run before committing)
```

```bash
make verify       # format-check + lint (ruff/eslint) + typecheck (mypy strict/tsc) + ui build
```

There is no test suite and none should be added (`AGENTS.md`). `make verify` plus a manual smoke check is the definition of done.

Scoped equivalents when iterating: `cd backend && uv run ruff check .` / `uv run mypy src`; `cd ui && npm run lint` / `npm run typecheck`.

## Architecture

Monorepo: `backend/` (FastAPI, Python 3.14, uv) and `ui/` (React 19 + Vite + TypeScript). They share no build tooling; the root `Makefile` is the only orchestrator.

Backend lives in `backend/src/information_retrieval/` and is layered with dependencies pointing inward — `presentation` and `infrastructure` may depend on `application`/`domain`; `domain` stays framework-free:

- `domain/` — entities and invariants, pure Python.
- `application/` — use cases plus the `ports.py` protocols they own (repositories, HTTP sources, storage). Application defines the interface; infrastructure implements it.
- `infrastructure/` — adapters: `config.py` (Pydantic Settings, the single runtime-config boundary, reads `backend/.env`) and port implementations.
- `presentation/http/` — routes, request/response schemas, and `dependencies.py` where concrete adapters are wired into use cases. `main.py` exposes `create_app` as an app factory.

Adding a capability normally means: entity in `domain` → use case + port in `application` → adapter in `infrastructure` → route/schema + wiring in `presentation/http`.

UI is feature-sliced under `ui/src`:

- `features/<feature>/{api,model,ui}` — per-feature code; components never call `fetch` directly, they go through the feature's `api/` module.
- `shared/api/http-client.ts` — the single HTTP boundary; only genuinely cross-feature code belongs in `shared/`.
- `app/App.tsx` composes features; `styles/global.css` holds global styling.

## Conventions

- Comments and docstrings on business logic explain WHY (invariant, design decision), never WHAT.
- No speculative abstractions, dependencies, or persistence layers without a current requirement in an approved spec.
- Python formatting is `uv run ruff format` only (never Black); UI formatting is the pinned repo-local Prettier via `npm run format`.
- `backend/.env` and `ui/.env` are local-only; the committed contract lives in the matching `.env.example`.
