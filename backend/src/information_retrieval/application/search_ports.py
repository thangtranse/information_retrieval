from typing import Protocol

from information_retrieval.domain.search import ArticleSearchCandidate


class ArticleSearchRepository(Protocol):
    def find_best_articles(
        self,
        query_embedding: list[float],
        model_name: str,
        limit: int,
    ) -> list[ArticleSearchCandidate]:
        """Return one exact best sentence per eligible article in stable score order."""
        ...
