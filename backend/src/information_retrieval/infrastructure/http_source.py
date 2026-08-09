import httpx

from information_retrieval.domain.errors import UpstreamFetchError

# A descriptive UA and bounded timeout keep the synchronous crawler polite and prevent a
# single unresponsive host from stalling the whole sequential run indefinitely.
_DEFAULT_HEADERS = {"User-Agent": "InformationRetrievalCrawler/0.1 (+sequential)"}
_DEFAULT_TIMEOUT = 15.0


class HttpxArticleSource:
    """Synchronous httpx implementation of the article source. Redirects are followed so we
    can inspect the final URL, but the host contract is re-checked by the use case, not here,
    keeping this adapter free of business policy."""

    def __init__(self, timeout: float = _DEFAULT_TIMEOUT) -> None:
        self._timeout = timeout

    def fetch_page(self, url: str) -> str:
        return self._get(url).text

    def fetch_article(self, url: str) -> tuple[str, str]:
        response = self._get(url)
        # Return the post-redirect URL so the caller can re-assert host scope; httpx exposes
        # the final location after following the redirect chain.
        return str(response.url), response.text

    def _get(self, url: str) -> httpx.Response:
        """Centralize the one network call so timeout, redirect and error-translation policy
        is identical for pages and articles, and no raw httpx error escapes the adapter."""
        try:
            with httpx.Client(
                follow_redirects=True,
                timeout=self._timeout,
                headers=_DEFAULT_HEADERS,
            ) as client:
                response = client.get(url)
                response.raise_for_status()
                return response
        except httpx.HTTPError as error:
            # Collapse the httpx exception hierarchy into the domain's upstream error without
            # leaking response bodies or internal detail into the failure reason.
            raise UpstreamFetchError(f"failed to fetch {url}: {type(error).__name__}") from error
