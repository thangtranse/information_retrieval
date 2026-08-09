# VnExpress Sequential Crawler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Hiện thực crawler tuần tự cho VnExpress theo `docs/superpowers/specs/2026-08-09-vnexpress-crawler-design.md`: khám phá URL bài viết từ seed pages, canonicalize chống trùng, tải nội dung thành file UTF-8 dạng block `<s>`, lưu trạng thái trong PostgreSQL/pgvector, chia sẻ cùng một use case tải bài giữa CLI batch script và FastAPI.

**Architecture:** Giữ dependency backend hướng vào trong. `domain` chứa entity, URL policy và text-file contract thuần Python. `application` sở hữu discovery use case, crawl-article use case (dùng chung) và các port. `infrastructure` triển khai httpx source, BeautifulSoup discovery/parser, SQLAlchemy repository và atomic UTF-8 writer. `presentation` cung cấp FastAPI route và CLI. Composition root nối adapter cụ thể vào use case.

**Tech Stack:** Python 3.14, uv, FastAPI, Pydantic Settings, httpx (sync), BeautifulSoup4, SQLAlchemy 2 + psycopg 3, PostgreSQL + pgvector, Docker Compose, Ruff, mypy.

## Global Constraints

- Chỉ hiện thực nội dung nằm trong "In scope" của spec; không concurrency, retry, embedding hay crawler UI.
- Không thêm automated tests (`AGENTS.md`).
- Docstring/comment chỉ giải thích WHY.
- Không thêm database abstraction ngoài port đang cần; không thêm Alembic ở phạm vi một bảng.
- Một canonicalization boundary duy nhất cho mọi URL trước validate/lookup/insert.
- Không thay đổi UI feature code ngoài cấu hình/build cần cho Compose.

## File Structure

```text
backend/
├── Dockerfile
├── pyproject.toml                                    # thêm httpx, bs4, sqlalchemy, psycopg
├── .env.example                                      # mở rộng contract crawler
├── data/articles/.gitkeep                            # giữ mount path
└── src/information_retrieval/
    ├── domain/
    │   ├── crawl.py                                  # CrawlUrl entity + status
    │   ├── article.py                                # ContentBlock + serialize `<s>`
    │   ├── url_policy.py                             # canonicalize + article-url invariant
    │   └── errors.py                                 # typed crawl errors
    ├── application/
    │   ├── crawler_ports.py                          # source/repository/storage ports
    │   ├── discover_articles.py                      # discovery use case
    │   └── crawl_article.py                          # shared crawl-article use case
    ├── infrastructure/
    │   ├── config.py                                 # + database_url, base_domain, seed_urls
    │   ├── database.py                               # engine + ORM model + schema init
    │   ├── crawl_repository.py                       # PostgreSQL repository
    │   ├── http_source.py                            # sync httpx source + redirect policy
    │   ├── vnexpress_discovery.py                    # anchor contract discovery
    │   ├── vnexpress_parser.py                       # article contract parser
    │   └── article_writer.py                         # atomic UTF-8 file storage
    └── presentation/
        ├── http/
        │   ├── schemas.py                            # + crawl request/response
        │   ├── dependencies.py                       # + crawl use-case wiring
        │   └── routes/crawler.py                     # POST /api/v1/crawler/articles
        └── cli/
            ├── __init__.py
            └── crawl.py                              # batch entrypoint
docker/postgres/init/00-extensions.sql               # enable vector
ui/Dockerfile
compose.yaml
Makefile                                             # + crawl target
README.md                                            # crawler + compose docs
.gitignore                                           # ignore data/articles/*.txt
```

## Tasks

### 1. Dependencies & config

- [x] Thêm `httpx`, `beautifulsoup4`, `sqlalchemy`, `psycopg[binary]` vào `backend/pyproject.toml` và `uv sync`.
- [x] Mở rộng `Settings` với `database_url`, `crawler_base_domain`, `crawler_seed_urls: list[str]`.
- [x] Mở rộng `backend/.env.example` theo Configuration Contract.

### 2. Domain

- [x] `domain/crawl.py`: `CrawlStatus` literal + `CrawlUrl` entity immutable.
- [x] `domain/url_policy.py`: `canonicalize(base, page_url, href) -> str | None` và `require_article_url(base, url) -> str`.
- [x] `domain/article.py`: `ContentBlock`, `serialize_article(docid, blocks) -> str` với wdcount + minimal escaping.
- [x] `domain/errors.py`: `InvalidArticleUrl`, `UpstreamFetchError`, `ArticleParseError`.

### 3. Application

- [x] `application/crawler_ports.py`: `ArticleSource`, `CrawlUrlRepository`, `ArticleFileStorage` protocols.
- [x] `application/discover_articles.py`: fetch seed, discover, canonicalize, insert pending, trả found/inserted/existing.
- [x] `application/crawl_article.py`: canonicalize+validate, insert/reuse, fetch, parse, atomic write, mark completed/failed; raise `ArticleCrawlFailed(row, category)`.

### 4. Infrastructure

- [x] `infrastructure/database.py`: engine, ORM `crawl_urls` (unique url, status check, tz timestamps), idempotent `create_all`.
- [x] `infrastructure/crawl_repository.py`: implement repository port.
- [x] `infrastructure/http_source.py`: sync httpx fetch page/article, validate final redirected host.
- [x] `infrastructure/vnexpress_discovery.py`: anchor contract → eligible hrefs.
- [x] `infrastructure/vnexpress_parser.py`: legacy/current `article.fck_detail` selectors → blocks.
- [x] `infrastructure/article_writer.py`: temp file + `os.replace`, trả relative `file_path`.

### 5. Presentation

- [x] `http/schemas.py`: `CrawlArticleRequest`, `CrawlArticleResponse`.
- [x] `http/dependencies.py`: build `CrawlArticle` với concrete adapters.
- [x] `http/routes/crawler.py`: POST route map error → 422/502/500.
- [x] `main.py`: include crawler router.
- [x] `presentation/cli/crawl.py`: batch flow + log format + exit code.

### 6. Deployment & docs

- [x] `backend/Dockerfile`, `ui/Dockerfile`.
- [x] `docker/postgres/init/00-extensions.sql` bật `vector`.
- [x] `compose.yaml`: postgres + backend + ui, healthcheck, bind mount `./backend/data`.
- [x] `backend/data/articles/.gitkeep`, `.gitignore` ignore `*.txt`.
- [x] `Makefile` thêm `crawl` target; cập nhật `README.md`.

### 7. Verification

- [x] `make format` && `make verify`.
- [x] `docker compose config` (live build/up cần môi trường người thực thi cho phép).
