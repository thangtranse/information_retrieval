from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Engine,
    String,
    Text,
    create_engine,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Single declarative base for the one business table; kept minimal so the single-table
    scope is not mistaken for an invitation to grow a generic ORM layer."""


class CrawlUrlRow(Base):
    __tablename__ = "crawl_urls"

    # A monotonic BIGINT id doubles as the file docid, so the artifact on disk is always
    # traceable to its row without a second identifier.
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # Uniqueness on the canonical URL is the last-resort guard against duplicate records
    # even if application-level checks race.
    url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    status: Mapped[str] = mapped_column(
        String(16),
        # The check constraint pins the same closed vocabulary the domain enforces, so a bad
        # write is rejected by the database and cannot corrupt downstream status logic.
        CheckConstraint(
            "status IN ('pending', 'completed', 'failed')",
            name="crawl_urls_status_check",
        ),
        nullable=False,
    )
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


def create_database_engine(database_url: str) -> Engine:
    """Build one engine per process. `pool_pre_ping` is enabled because the crawler and the
    Compose Postgres can outlive idle connections, and a stale socket must not fail a crawl."""
    return create_engine(database_url, pool_pre_ping=True, future=True)


def initialize_schema(engine: Engine) -> None:
    """Create the table idempotently at startup. `create_all` is a no-op when the table
    already exists, which satisfies the spec's idempotent-init requirement without Alembic."""
    Base.metadata.create_all(engine)
