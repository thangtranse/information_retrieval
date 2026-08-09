import re

from bs4 import BeautifulSoup, Tag

from information_retrieval.domain.url_policy import canonicalize

_WHITESPACE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    """Collapse whitespace runs so the anchor title/text comparison judges wording, not the
    incidental spacing VnExpress markup carries."""
    return _WHITESPACE.sub(" ", text).strip()


class VnExpressDiscoverer:
    """Discover article links from a VnExpress category page using the anchor contract. The
    contract is deliberately strict so navigation, promo and widget links never enter the
    crawl queue as false article candidates."""

    def __init__(self, base_domain: str) -> None:
        self._base_domain = base_domain

    def discover(self, page_url: str, html: str) -> list[str]:
        """Return canonical article URLs for anchors that satisfy every contract condition.

        An anchor qualifies when it has `href`, a non-empty `title`, visible text, and its
        title and text agree after normalization. VnExpress no longer consistently emits
        analytics attributes such as `data-itm-source`, so those attributes cannot be part of
        the stable article-link contract. Non-qualifying anchors are silently skipped.
        """
        soup = BeautifulSoup(html, "html.parser")
        results: list[str] = []
        for anchor in soup.find_all("a"):
            if not isinstance(anchor, Tag):
                continue

            href = anchor.get("href")
            title = anchor.get("title")
            if not isinstance(href, str) or not href.strip():
                continue
            if not isinstance(title, str) or not title.strip():
                continue

            visible = _normalize(anchor.get_text())
            if not visible:
                continue

            normalized_title = _normalize(title)
            folded_title = normalized_title.casefold()
            folded_visible = visible.casefold()
            # Titles and visible text often differ by a trailing summary, so accept when one
            # contains the other rather than demanding an exact match.
            if not (
                folded_title == folded_visible
                or folded_title in folded_visible
                or folded_visible in folded_title
            ):
                continue

            canonical = canonicalize(self._base_domain, page_url, href)
            if canonical is not None:
                results.append(canonical)
        return results
