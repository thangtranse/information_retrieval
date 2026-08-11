from pathlib import Path
from typing import cast

from bs4 import BeautifulSoup

from information_retrieval.domain.article import BlockType
from information_retrieval.domain.preprocessing import (
    ArticlePreprocessingError,
    SourceParagraph,
)

_BACKEND_ROOT = Path(__file__).resolve().parents[3]


def _resolve_backend_path(stored_path: str) -> Path:
    """Anchor persisted relative paths to backend so CLI cwd cannot redirect file access."""
    raw_path = Path(stored_path)
    if raw_path.is_absolute():
        candidate = raw_path.resolve()
    elif raw_path.parts and raw_path.parts[0] == "backend":
        candidate = (_BACKEND_ROOT.parent / raw_path).resolve()
    else:
        candidate = (_BACKEND_ROOT / raw_path).resolve()

    if not candidate.is_relative_to(_BACKEND_ROOT):
        raise ArticlePreprocessingError(f"file_path escapes backend directory: {stored_path}")
    return candidate


class Utf8ArticleParagraphReader:
    _ALLOWED_TYPES = {"title", "description", "paragraph"}

    def read(self, crawl_id: int, file_path: str) -> list[SourceParagraph]:
        """Fail the whole document before persistence when source metadata is inconsistent."""
        resolved_path = _resolve_backend_path(file_path)
        try:
            serialized = resolved_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise ArticlePreprocessingError(
                f"cannot read UTF-8 article file {file_path}: {error}"
            ) from error

        # The corpus serializer represents source `>` characters as this literal entity;
        # removing it before HTML decoding avoids deleting unrelated greater-than characters.
        soup = BeautifulSoup(serialized.replace("&gt;", ""), "html.parser")
        paragraphs: list[SourceParagraph] = []
        for tag in soup.find_all("s"):
            try:
                docid = int(str(tag["docid"]))
                num = int(str(tag["num"]))
                source_word_count = int(str(tag["wdcount"]))
                block_type = str(tag["type"])
            except (KeyError, TypeError, ValueError) as error:
                raise ArticlePreprocessingError(f"invalid <s> metadata in {file_path}") from error

            if docid != crawl_id:
                raise ArticlePreprocessingError(
                    f"docid {docid} does not match crawl_urls.id {crawl_id}"
                )
            if num <= 0 or source_word_count < 0 or block_type not in self._ALLOWED_TYPES:
                raise ArticlePreprocessingError(
                    f"invalid <s> values for crawl_urls.id {crawl_id}, num {num}"
                )
            if paragraphs and num <= paragraphs[-1].num:
                raise ArticlePreprocessingError(
                    f"paragraph num is not strictly increasing for crawl_urls.id {crawl_id}"
                )

            text = tag.get_text(separator=" ", strip=True)
            paragraphs.append(
                SourceParagraph(
                    docid=docid,
                    num=num,
                    source_word_count=source_word_count,
                    block_type=cast(BlockType, block_type),
                    text=text,
                )
            )

        if not paragraphs:
            raise ArticlePreprocessingError(f"no valid <s> blocks in {file_path}")
        return paragraphs
