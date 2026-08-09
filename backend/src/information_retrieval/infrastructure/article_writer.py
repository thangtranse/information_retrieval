import os
import tempfile
from pathlib import Path

# All article files live under a fixed relative directory so the path stored in the database
# is stable across the CLI, the API and the Docker bind mount that all run from backend/.
_ARTICLES_DIR = Path("data") / "articles"


class Utf8ArticleFileStorage:
    """Write article files atomically as UTF-8. The temp-then-replace sequence guarantees a
    reader never observes a half-written file and the row only completes once the final file
    is durable."""

    def __init__(self, base_dir: Path = _ARTICLES_DIR) -> None:
        self._base_dir = base_dir

    def write(self, crawl_id: int, serialized: str) -> str:
        """Persist the serialized article to `<base>/<id>.txt` and return its backend-relative
        path. The temp file is created in the destination directory so `os.replace` is a true
        atomic rename on the same filesystem rather than a cross-device copy."""
        self._base_dir.mkdir(parents=True, exist_ok=True)
        target = self._base_dir / f"{crawl_id}.txt"

        fd, temp_name = tempfile.mkstemp(dir=self._base_dir, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(serialized)
            os.replace(temp_name, target)
        except BaseException:
            # Never leave a stray temp file behind if the write or replace fails midway.
            Path(temp_name).unlink(missing_ok=True)
            raise

        return target.as_posix()
