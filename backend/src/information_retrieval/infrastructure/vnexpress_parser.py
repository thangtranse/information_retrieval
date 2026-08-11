import re

from bs4 import BeautifulSoup, Tag

from information_retrieval.domain.article import BlockType, ContentBlock
from information_retrieval.domain.errors import ArticleParseError

_WHITESPACE = re.compile(r"\s+")

# Keep the legacy id-qualified selector first while accepting the current VnExpress markup,
# where the same article container keeps `fck_detail` but no longer carries the gallery id.
_ARTICLE_SELECTOR = "article#fck_detail_gallery.fck_detail, article.fck_detail"
_FALLBACK_ARTICLE_SELECTOR = "article.clearfix"
_FALLBACK_CONTENT_SELECTOR = "section#fck_detail_gallery, section.fck_detail"


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
            article = self._find_fallback_article(soup)
        if article is None:
            raise ArticleParseError(
                f"{_ARTICLE_SELECTOR} not found and no supported clearfix fallback found"
            )

        blocks: list[ContentBlock] = []
        has_title = False
        is_medium_editor = article.get("id") == "medium_editor"
        # A single ordered pass preserves the author's block sequence, which the file's `num`
        # ordering must mirror.
        for element in article.find_all(["h1", "h2", "p"]):
            if not isinstance(element, Tag):
                continue
            if (
                is_medium_editor
                and element.name == "p"
                and element.find_parent("figcaption") is not None
            ):
                continue
            block_type = self._classify(element, is_medium_editor=is_medium_editor)
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
    def _find_fallback_article(soup: BeautifulSoup) -> Tag | None:
        """Use the live-report layout only after legacy/current article selectors fail.

        Requiring the nested content section prevents a generic `article.clearfix` wrapper
        from becoming an accidental article root while preserving all existing parsing paths.
        """
        for candidate in soup.select(_FALLBACK_ARTICLE_SELECTOR):
            if isinstance(candidate, Tag) and candidate.select_one(_FALLBACK_CONTENT_SELECTOR):
                return candidate
        return None

    @staticmethod
    def _classify(element: Tag, *, is_medium_editor: bool) -> BlockType | None:
        """Extend classification only for the medium-editor layout so accepting its plain
        paragraphs and `h2.title` cannot broaden the established article contracts."""
        if element.name == "h1":
            return "title"
        classes: list[str] = element.get("class") or []  # type: ignore[assignment]
        if is_medium_editor and element.name == "h2" and "title" in classes:
            return "title"
        if element.name == "p":
            if "description" in classes:
                return "description"
            if "Normal" in classes:
                return "paragraph"
            if is_medium_editor and not classes:
                return "paragraph"
        return None
