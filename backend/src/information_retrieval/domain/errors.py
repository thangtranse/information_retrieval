class InvalidArticleUrl(ValueError):
    """Raised when a URL fails the canonicalization policy before any row is created, so the
    delivery layer can reject the request without ever touching persistent state."""


class UpstreamFetchError(Exception):
    """Raised for network, redirect-policy or HTTP-status failures reaching the source. Kept
    distinct from parse failures so the HTTP boundary can map upstream problems to 502."""


class ArticleParseError(Exception):
    """Raised when fetched HTML does not satisfy the article contract. Distinct from upstream
    errors so a structurally invalid document maps to 422 rather than a gateway error."""
