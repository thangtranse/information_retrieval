import re

from bs4 import BeautifulSoup, Tag

from information_retrieval.domain.article import BlockType, ContentBlock
from information_retrieval.domain.errors import ArticleParseError

_WHITESPACE = re.compile(r"\s+")

# Keep the legacy id-qualified selector first while accepting the current VnExpress markup,
# where the same article container keeps `fck_detail` but no longer carries the gallery id.
_ARTICLE_SELECTOR = "article#fck_detail_gallery.fck_detail, article.fck_detail"


def _normalize(text: str) -> str:
    """Decode is handled by the parser; here we only collapse whitespace so `wdcount` and the
    stored text are computed on the same canonical form the file contract promises."""
    return _WHITESPACE.sub(" ", text).strip()


class VnExpressParser:
    """Extract ordered content blocks from a VnExpress article body. Recognizes only the
    element contract the spec fixes, so any structural drift surfaces as an explicit parse
    failure instead of a silently empty or malformed file."""

    def extract(self, html: str) -> list[ContentBlock]:
        """Walk the article container in DOM order, emitting one block per recognized element.

        A missing container, a missing title, or no content at all are treated as distinct
        contract violations because they signal the page is not the article we expected, and
        an empty file must never be presented as a successful crawl.
        """
        soup = BeautifulSoup(html, "html.parser")
        article = soup.select_one(_ARTICLE_SELECTOR)
        if article is None:
            raise ArticleParseError(f"{_ARTICLE_SELECTOR} not found")

        blocks: list[ContentBlock] = []
        has_title = False
        # A single ordered pass preserves the author's block sequence, which the file's `num`
        # ordering must mirror.
        for element in article.find_all(["h1", "p"]):
            if not isinstance(element, Tag):
                continue
            block_type = self._classify(element)
            if block_type is None:
                continue
            text = _normalize(element.get_text())
            if not text:
                continue
            if block_type == "title":
                has_title = True
            blocks.append(ContentBlock(type=block_type, text=text))

        if not has_title:
            raise ArticleParseError("article has no title block")
        if not blocks:
            raise ArticleParseError("article has no content blocks")
        return blocks

    @staticmethod
    def _classify(element: Tag) -> BlockType | None:
        """Map an element to its block type by the exact tag/class contract, returning None
        for anything outside it so unrelated markup is ignored rather than misclassified."""
        if element.name == "h1":
            return "title"
        classes: list[str] = element.get("class") or []  # type: ignore[assignment]
        if element.name == "p":
            if "description" in classes:
                return "description"
            if "Normal" in classes:
                return "paragraph"
        return None
