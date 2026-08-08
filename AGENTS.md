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
