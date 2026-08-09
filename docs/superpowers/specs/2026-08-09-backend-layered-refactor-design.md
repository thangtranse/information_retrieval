# Backend Layered Package Refactor Design

## Goal

Refactor backend hiện tại thành các package chi tiết theo trách nhiệm trong từng Clean Architecture layer, giữ nguyên toàn bộ behavior của health check và VnExpress crawler.

## Scope

- Di chuyển toàn bộ code hiện tại dưới `backend/src/information_retrieval/`.
- Cập nhật import nội bộ, composition root, HTTP dependencies, CLI và Makefile khi cần.
- Giữ nguyên API routes, request/response payloads, CLI command, database table/schema, environment variables, Docker behavior và file output contract.
- Không thêm automated tests, business feature, dependency hoặc abstraction rỗng.
- Không tạo package `user`, `auth` hoặc thư mục không có module thực tế.

## Dependency Direction

```text
presentation ─┐
              ├──> application ──> domain
infrastructure┘
```

- `domain` chỉ dùng Python standard library và domain modules.
- `application` chỉ phụ thuộc `domain` và application-owned ports/DTO/exceptions.
- `infrastructure` triển khai application ports và có thể phụ thuộc domain.
- `presentation` gọi application use cases; concrete wiring được giữ tại presentation edge và `main.py`.

## Target Structure

```text
backend/src/information_retrieval/
├── domain/
│   ├── models/
│   │   ├── crawl_url.py
│   │   └── health_status.py
│   ├── value_objects/
│   │   └── content_block.py
│   ├── exceptions/
│   │   ├── article.py
│   │   └── url.py
│   └── services/
│       ├── article_serializer.py
│       └── url_policy.py
├── application/
│   ├── ports/
│   │   ├── article_discoverer.py
│   │   ├── article_parser.py
│   │   ├── article_source.py
│   │   ├── article_storage.py
│   │   ├── crawl_url_repository.py
│   │   └── health_probe.py
│   ├── use_cases/
│   │   ├── crawl_article.py
│   │   ├── discover_articles.py
│   │   └── get_health.py
│   ├── dto/
│   │   └── discovery_result.py
│   └── exceptions/
│       └── crawl.py
├── infrastructure/
│   ├── config/
│   │   └── settings.py
│   ├── database/
│   │   ├── base.py
│   │   ├── engine.py
│   │   ├── schema.py
│   │   └── models/crawl_url.py
│   ├── repositories/postgres_crawl_url_repository.py
│   ├── sources/httpx_article_source.py
│   ├── parsers/vnexpress_parser.py
│   ├── discoverers/vnexpress_discoverer.py
│   ├── storage/utf8_article_file_storage.py
│   └── health/system_health_probe.py
├── presentation/
│   ├── http/
│   │   ├── routes/
│   │   │   ├── crawler.py
│   │   │   └── health.py
│   │   ├── schemas/
│   │   │   ├── crawler.py
│   │   │   └── health.py
│   │   └── dependencies/
│   │       ├── crawler.py
│   │       └── health.py
│   └── cli/crawl.py
└── main.py
```

Every package directory contains `__init__.py`. Package initializers remain empty; callers import from the owning module so interfaces have one canonical definition.

## Migration Map

### Domain

- `domain/crawl.py` → `domain/models/crawl_url.py`.
- `domain/health.py` → `domain/models/health_status.py`.
- `ContentBlock` and `BlockType` from `domain/article.py` → `domain/value_objects/content_block.py`.
- `_escape()` and `serialize_article()` from `domain/article.py` → `domain/services/article_serializer.py`.
- `InvalidArticleUrl` from `domain/errors.py` → `domain/exceptions/url.py`.
- `UpstreamFetchError` and `ArticleParseError` → `domain/exceptions/article.py`.
- `domain/url_policy.py` → `domain/services/url_policy.py`.

### Application

- Split `application/crawler_ports.py` into one module per port under `application/ports/`.
- Move current health port from `application/ports.py` to `application/ports/health_probe.py`.
- Move use cases to `application/use_cases/` without changing public class names or signatures.
- Move `DiscoveryResult` to `application/dto/discovery_result.py`.
- Move `ArticleCrawlFailed` to `application/exceptions/crawl.py`.

### Infrastructure

- `infrastructure/config.py` → `infrastructure/config/settings.py`.
- Split `infrastructure/database.py` into declarative base, ORM model, engine factory and schema initialization modules.
- Move repository, source, parser, discoverer, storage and health adapter into responsibility-specific packages without changing their public class names.

### Presentation

- Split `presentation/http/schemas.py` into crawler and health schema modules.
- Split `presentation/http/dependencies.py` into crawler and health dependency modules.
- Preserve route module filenames and route paths.
- Update CLI imports only; `python -m information_retrieval.presentation.cli.crawl` remains unchanged.

## Behavior Contracts Preserved

- `GET /api/v1/health` response shape and values.
- `POST /api/v1/crawler/articles` request, response and failure status mapping.
- Crawl URL canonicalization and seed validation.
- Article extraction and `<s>` serialization contract.
- PostgreSQL table `crawl_urls`, constraints and row mapping.
- Atomic UTF-8 article storage under `data/articles`.
- CLI discovery/crawl order, output messages and exit code.
- Settings names, `APP_` environment prefix and `.env` loading.

## Verification

The repository intentionally has no automated tests. Verification consists of:

- `make format` followed by `make verify`.
- Import smoke checks for every moved public class/function.
- FastAPI route inspection confirming both existing route paths.
- SQLAlchemy metadata inspection confirming table name and columns.
- CLI module import and `--help`-independent import smoke check without starting network/database work.
- `rg` scan confirming no imports reference deleted flat modules.
- `git diff --check` and review that changes are moves/import rewrites rather than behavior changes.

## Risks and Controls

- **Missed imports:** scan all backend imports after moves and import every public entrypoint.
- **Circular imports:** keep DTOs and application exceptions separate from use cases; ports only import domain types.
- **Database drift:** split declarations without changing column definitions or constraint text.
- **Behavior drift:** do not rename public classes/functions, modify function bodies, or change route/CLI contracts.
- **Empty architecture:** create only directories containing migrated modules.
