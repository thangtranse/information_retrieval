from dataclasses import dataclass
from datetime import datetime
from typing import Literal

# The status vocabulary is fixed by the spec so both the database check constraint and
# the application flow reason about the exact same closed set of processing outcomes.
CrawlStatus = Literal["pending", "completed", "failed"]


@dataclass(frozen=True, slots=True)
class CrawlUrl:
    """Model one tracked article URL as an immutable snapshot so adapters cannot mutate
    persisted state in place and silently diverge from the row the repository returned."""

    id: int
    url: str
    status: CrawlStatus
    file_path: str | None
    error_reason: str | None
    created_at: datetime
    updated_at: datetime
