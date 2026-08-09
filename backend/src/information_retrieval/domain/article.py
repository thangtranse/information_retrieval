from dataclasses import dataclass
from typing import Literal

from information_retrieval.domain.errors import ArticleParseError

BlockType = Literal["title", "description", "paragraph"]


@dataclass(frozen=True, slots=True)
class ContentBlock:
    """One extracted, already whitespace-normalized unit of article text. Normalization is
    the parser's job; keeping it a precondition here means serialization stays a pure,
    deterministic transform of trusted input."""

    type: BlockType
    text: str


def _escape(text: str) -> str:
    """Escape only the three characters that could break the surrounding `<s>` tag. A full
    HTML escape is avoided so downstream tooling reads the original punctuation verbatim."""
    # Ampersand must be replaced first, otherwise it would double-escape the entities
    # produced for the angle brackets.
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def serialize_article(docid: int, blocks: list[ContentBlock]) -> str:
    """Render blocks into the line-per-block `<s>` file contract keyed by the database id.

    `docid` is the persisted row id so a file can always be traced back to its record, and
    `num` is regenerated from position so ordering invariants never depend on the caller.
    """
    if not blocks:
        raise ArticleParseError("article produced no content blocks")

    lines = []
    for index, block in enumerate(blocks, start=1):
        # wdcount is defined against the normalized text, so a plain whitespace split is the
        # authoritative token count rather than a separate heuristic.
        word_count = len(block.text.split())
        lines.append(
            f'<s docid="{docid}" num="{index}" wdcount="{word_count}" '
            f'type="{block.type}">{_escape(block.text)}</s>'
        )
    return "\n".join(lines) + "\n"
