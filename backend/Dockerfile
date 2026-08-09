# Python 3.14 base; uv is copied from its published image so the container uses the exact
# same installer and lockfile resolution as local development.
FROM python:3.14-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy bytecode and use plain file copies so the image works on any storage driver, and keep
# the venv inside the project so `uv run` resolves it deterministically.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

# Install dependencies before the source so dependency layers cache across code changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
RUN uv sync --frozen --no-dev

EXPOSE 8000

# Default command runs the API; the same image runs the batch crawler by overriding the
# command with `uv run python -m information_retrieval.presentation.cli.crawl`.
CMD ["uv", "run", "uvicorn", "information_retrieval.main:create_app", \
     "--factory", "--host", "0.0.0.0", "--port", "8000"]
