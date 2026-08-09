from urllib.parse import urljoin, urlsplit, urlunsplit

from information_retrieval.domain.errors import InvalidArticleUrl


def _normalize_host(host: str) -> str:
    """Fold host casing and trailing dot so redirect targets and configured base compare
    on the identity the DNS/HTTP stack actually resolves, not on incidental formatting."""
    return host.strip().rstrip(".").lower()


def canonicalize(base_domain: str, page_url: str, href: str) -> str | None:
    """Reduce any anchor href to the single canonical form used for validation, lookup and
    insert, returning None when the target is not an in-scope VnExpress article.

    Collapsing query and fragment here is what makes the unique URL constraint meaningful:
    the same article reached through different tracking parameters maps to one row.
    """
    candidate = href.strip()
    if not candidate:
        return None

    # Resolve relative links against the page that contained the anchor before any host
    # check, otherwise same-site relative hrefs would be rejected as foreign.
    absolute = urljoin(page_url, candidate)
    parts = urlsplit(absolute)

    if parts.scheme not in ("http", "https"):
        return None

    base_host = _normalize_host(urlsplit(base_domain).hostname or "")
    if not base_host or _normalize_host(parts.hostname or "") != base_host:
        return None

    # Dropping query and fragment is the deduplication boundary; the path alone identifies
    # the article. Empty paths cannot be articles.
    path = parts.path
    if not path.endswith(".html"):
        return None

    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def require_article_url(base_domain: str, url: str) -> str:
    """Canonicalize a caller-supplied URL and reject it before any row is created when it
    is not an in-scope article, so an invalid manual request never pollutes the table.

    The page context is the URL itself: a manual request is always an absolute URL.
    """
    canonical = canonicalize(base_domain, url, url)
    if canonical is None:
        raise InvalidArticleUrl(
            "URL must use http(s), belong to the configured host and end with .html"
        )
    return canonical


def require_seed_url(base_domain: str, url: str) -> str:
    """Reject an out-of-scope seed before any network access so configuration cannot make
    the discovery use case fetch an unintended host; category paths do not require `.html`."""
    parts = urlsplit(url.strip())
    base_host = _normalize_host(urlsplit(base_domain).hostname or "")
    if (
        parts.scheme not in ("http", "https")
        or not base_host
        or _normalize_host(parts.hostname or "") != base_host
    ):
        raise InvalidArticleUrl("Seed URL must use http(s) and belong to the configured host")
    return urlunsplit((parts.scheme, parts.netloc, parts.path or "/", "", ""))
