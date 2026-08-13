import asyncio
from time import monotonic
from urllib.parse import urljoin

import httpx

from information_retrieval.domain.errors import InvalidArticleUrl, UpstreamFetchError
from information_retrieval.domain.url_policy import require_article_url

_MAX_HTML_BYTES = 2 * 1024 * 1024
_MAX_REDIRECTS = 5
_PREVIEW_HEADERS = {
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Encoding": "identity",
    "User-Agent": "InformationRetrievalPreview/0.1",
}


class HttpxArticlePreviewSource:
    def __init__(self, base_domain: str, timeout: float = 5.0) -> None:
        self._base_domain = base_domain
        self._timeout = timeout

    async def fetch(self, url: str) -> tuple[str, str]:
        """Validate every redirect before following it so preview cannot leave the source host."""
        current_url = require_article_url(self._base_domain, url)
        deadline = monotonic() + self._timeout
        try:
            # WHY: HTTPX timeouts apply per network operation; one cancellation scope is needed
            # to cap redirects, connection setup and streaming under the same wall-clock budget.
            async with asyncio.timeout(self._timeout):
                async with httpx.AsyncClient(
                    timeout=self._timeout, headers=_PREVIEW_HEADERS
                ) as client:
                    for redirect_count in range(_MAX_REDIRECTS + 1):
                        remaining_seconds = deadline - monotonic()
                        if remaining_seconds <= 0:
                            raise UpstreamFetchError("preview exceeded its request deadline")
                        async with client.stream(
                            "GET",
                            current_url,
                            follow_redirects=False,
                            timeout=remaining_seconds,
                        ) as response:
                            if response.is_redirect:
                                if redirect_count == _MAX_REDIRECTS:
                                    raise UpstreamFetchError("preview exceeded redirect limit")
                                location = response.headers.get("location")
                                if not location:
                                    raise UpstreamFetchError("preview redirect omitted location")
                                current_url = require_article_url(
                                    self._base_domain, urljoin(current_url, location)
                                )
                                continue

                            response.raise_for_status()
                            content_type = response.headers.get("content-type", "").lower()
                            if not (
                                content_type.startswith("text/html")
                                or content_type.startswith("application/xhtml+xml")
                            ):
                                raise UpstreamFetchError("preview response is not HTML")

                            content_encoding = response.headers.get("content-encoding", "identity")
                            if content_encoding.lower() not in {"", "identity"}:
                                raise UpstreamFetchError(
                                    "preview response used compressed encoding"
                                )

                            declared_size = response.headers.get("content-length")
                            if declared_size and int(declared_size) > _MAX_HTML_BYTES:
                                raise UpstreamFetchError("preview HTML exceeds 2 MiB")

                            body = bytearray()
                            async for chunk in response.aiter_raw():
                                remaining_bytes = _MAX_HTML_BYTES - len(body)
                                if len(chunk) > remaining_bytes:
                                    raise UpstreamFetchError("preview HTML exceeds 2 MiB")
                                body.extend(chunk)

                            encoding = response.encoding or "utf-8"
                            return current_url, body.decode(encoding, errors="replace")
        except TimeoutError as error:
            raise UpstreamFetchError("preview exceeded its request deadline") from error
        except (httpx.HTTPError, InvalidArticleUrl, LookupError, UnicodeError, ValueError) as error:
            raise UpstreamFetchError(
                f"failed to fetch article preview: {type(error).__name__}"
            ) from error

        raise UpstreamFetchError("preview redirect flow did not produce HTML")
