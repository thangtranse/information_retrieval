from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from information_retrieval.domain.article_preview import ArticlePreview


def _clean(value: str | None) -> str | None:
    """Collapse source formatting so metadata remains compact and safe for card rendering."""
    if value is None:
        return None
    normalized = " ".join(value.split())
    return normalized or None


class OpenGraphArticlePreviewParser:
    def parse(self, page_url: str, html: str) -> ArticlePreview:
        """Prefer Open Graph while retaining standard HTML metadata as a resilient fallback."""
        soup = BeautifulSoup(html, "html.parser")

        def meta_content(
            *, property_name: str | None = None, name: str | None = None
        ) -> str | None:
            # WHY: Attribute-based selection avoids interpreting arbitrary page text as metadata.
            if property_name is not None:
                tag = soup.find("meta", attrs={"property": property_name})
            elif name is not None:
                tag = soup.find("meta", attrs={"name": name})
            else:
                return None
            return _clean(str(tag.get("content"))) if tag and tag.get("content") else None

        title = meta_content(property_name="og:title")
        if title is None and soup.title is not None:
            title = _clean(soup.title.get_text(" ", strip=True))

        description = meta_content(property_name="og:description") or meta_content(
            name="description"
        )
        image = meta_content(property_name="og:image")
        image_url = urljoin(page_url, image) if image else None
        if image_url and urlsplit(image_url).scheme not in {"http", "https"}:
            image_url = None

        return ArticlePreview(
            title=title,
            description=description,
            image_url=image_url,
            site_name=meta_content(property_name="og:site_name"),
        )
