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
