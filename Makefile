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
