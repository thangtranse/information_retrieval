import base64
import binascii
import json
from dataclasses import dataclass
from datetime import datetime

from information_retrieval.application.article_catalog_ports import CrawledArticleCatalog
from information_retrieval.domain.crawl import CrawlUrl

_CURSOR_VERSION = 1


class InvalidCrawledArticleCursor(ValueError):
    """Mark malformed client cursors without leaking decoding internals through HTTP."""


@dataclass(frozen=True, slots=True)
class CrawledArticleCursor:
    updated_at: datetime
    id: int


@dataclass(frozen=True, slots=True)
class CrawledArticlePage:
    items: list[CrawlUrl]
    next_cursor: str | None


def encode_cursor(cursor: CrawledArticleCursor) -> str:
    """Keep the keyset representation opaque so clients cannot depend on storage details."""
    payload = json.dumps(
        {"v": _CURSOR_VERSION, "updated_at": cursor.updated_at.isoformat(), "id": cursor.id},
        separators=(",", ":"),
    ).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def decode_cursor(raw_cursor: str) -> CrawledArticleCursor:
    """Reject every non-versioned or structurally invalid cursor as one public error type."""
    try:
        padding = "=" * (-len(raw_cursor) % 4)
        decoded = base64.b64decode(raw_cursor + padding, altchars=b"-_", validate=True)
        payload = json.loads(decoded.decode("utf-8"))
        if not isinstance(payload, dict) or payload.get("v") != _CURSOR_VERSION:
            raise InvalidCrawledArticleCursor("unsupported cursor")
        updated_at = datetime.fromisoformat(payload["updated_at"])
        crawl_id = payload["id"]
        if updated_at.tzinfo is None or not isinstance(crawl_id, int) or crawl_id <= 0:
            raise InvalidCrawledArticleCursor("invalid cursor values")
        return CrawledArticleCursor(updated_at=updated_at, id=crawl_id)
    except (
        binascii.Error,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        UnicodeDecodeError,
        ValueError,
    ) as error:
        if isinstance(error, InvalidCrawledArticleCursor):
            raise
        raise InvalidCrawledArticleCursor("invalid cursor") from error


class ListCrawledArticles:
    def __init__(self, catalog: CrawledArticleCatalog) -> None:
        self._catalog = catalog

    def execute(self, *, limit: int, cursor: str | None) -> CrawledArticlePage:
        """Read one extra row so page completion never requires an expensive count query."""
        decoded = decode_cursor(cursor) if cursor is not None else None
        rows = self._catalog.list_completed_after(
            limit=limit + 1,
            updated_before=decoded.updated_at if decoded else None,
            id_before=decoded.id if decoded else None,
        )
        items = rows[:limit]
        next_cursor = None
        if len(rows) > limit:
            boundary = items[-1]
            next_cursor = encode_cursor(
                CrawledArticleCursor(updated_at=boundary.updated_at, id=boundary.id)
            )
        return CrawledArticlePage(items=items, next_cursor=next_cursor)
