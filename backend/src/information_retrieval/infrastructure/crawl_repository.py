from typing import cast

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from information_retrieval.domain.crawl import CrawlStatus, CrawlUrl
from information_retrieval.infrastructure.database import CrawlUrlRow, initialize_schema


class PostgresCrawlUrlRepository:
    """Adapt the crawl-url table to the application repository port. Each method opens its
    own short transaction so a single failed URL never leaves a wider unit of work open."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def initialize_schema(self) -> None:
        initialize_schema(self._engine)

    def get_by_url(self, url: str) -> CrawlUrl | None:
        with Session(self._engine) as session:
            row = session.scalar(select(CrawlUrlRow).where(CrawlUrlRow.url == url))
            return self._to_domain(row) if row is not None else None

    def insert_pending(self, url: str) -> CrawlUrl:
        with Session(self._engine) as session, session.begin():
            row = CrawlUrlRow(url=url, status="pending")
            session.add(row)
            # Flush so the database assigns the id before we detach the row into a domain
            # object the caller uses as the file docid.
            session.flush()
            return self._to_domain(row)

    def list_failed(self) -> list[CrawlUrl]:
        """Use id ordering so explicit retry runs remain deterministic and easy to audit."""
        with Session(self._engine) as session:
            rows = session.scalars(
                select(CrawlUrlRow).where(CrawlUrlRow.status == "failed").order_by(CrawlUrlRow.id)
            ).all()
            return [self._to_domain(row) for row in rows]

    def list_completed(self, crawl_id: int | None = None) -> list[CrawlUrl]:
        """Only expose durable files, in id order, so reruns are reproducible and auditable."""
        with Session(self._engine) as session:
            statement = select(CrawlUrlRow).where(
                CrawlUrlRow.status == "completed",
                CrawlUrlRow.file_path.is_not(None),
            )
            if crawl_id is not None:
                statement = statement.where(CrawlUrlRow.id == crawl_id)
            rows = session.scalars(statement.order_by(CrawlUrlRow.id)).all()
            return [self._to_domain(row) for row in rows]

    def mark_completed(self, crawl_id: int, file_path: str) -> CrawlUrl:
        return self._update(crawl_id, status="completed", file_path=file_path, error_reason=None)

    def mark_failed(self, crawl_id: int, error_reason: str) -> CrawlUrl:
        # file_path is intentionally omitted so a file kept from a prior success survives a
        # later failed re-crawl; only status and reason reflect the latest attempt.
        return self._update(crawl_id, status="failed", error_reason=error_reason)

    def _update(
        self,
        crawl_id: int,
        *,
        status: CrawlStatus,
        error_reason: str | None,
        file_path: str | None = None,
    ) -> CrawlUrl:
        with Session(self._engine) as session, session.begin():
            row = session.get(CrawlUrlRow, crawl_id)
            if row is None:
                raise LookupError(f"crawl_urls row {crawl_id} disappeared during processing")
            row.status = status
            row.error_reason = error_reason
            if file_path is not None:
                row.file_path = file_path
            session.flush()
            return self._to_domain(row)

    @staticmethod
    def _to_domain(row: CrawlUrlRow) -> CrawlUrl:
        """Translate the persistence row into the immutable domain entity so callers never
        hold a live ORM object bound to a closed session."""
        return CrawlUrl(
            id=row.id,
            url=row.url,
            # The database check constraint guarantees the value is in the closed set, so the
            # cast documents that invariant for the type checker.
            status=cast(CrawlStatus, row.status),
            file_path=row.file_path,
            error_reason=row.error_reason,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
