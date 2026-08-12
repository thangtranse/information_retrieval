.PHONY: setup dev-backend dev-ui crawl download-segmenter-model preprocess segment embed format format-check lint typecheck build verify

setup:
	uv python install 3.14
	cd backend && uv sync
	cd ui && npm ci

dev-backend:
	cd backend && uv run uvicorn information_retrieval.main:create_app --factory --reload

dev-ui:
	cd ui && npm run dev

crawl:
	cd backend && uv run python -m information_retrieval.presentation.cli.crawl $(ARGS)

download-segmenter-model:
	cd backend && uv run python -m information_retrieval.presentation.cli.segment --download-model-only

preprocess:
	cd backend && uv run python -m information_retrieval.presentation.cli.preprocess $(if $(CRAWL_ID),--crawl-id=$(CRAWL_ID),)

segment:
	cd backend && uv run python -m information_retrieval.presentation.cli.segment $(if $(CRAWL_ID),--crawl-id=$(CRAWL_ID),)

embed:
	cd backend && uv run python -m information_retrieval.presentation.cli.embed $(if $(CRAWL_ID),--crawl-id=$(CRAWL_ID),)

format:
	cd backend && uv run ruff format .
	cd ui && npm run format

format-check:
	cd backend && uv run ruff format --check .
	cd ui && npm run format:check

lint:
	cd backend && uv run ruff check .
	cd ui && npm run lint

typecheck:
	cd backend && uv run mypy src
	cd ui && npm run typecheck

build:
	cd ui && npm run build

verify: format-check lint typecheck build
