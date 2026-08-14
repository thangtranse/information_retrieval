from information_retrieval.application.crawler_ports import ArticleFileStorage, CrawlUrlRepository
from information_retrieval.domain.article import ContentBlock, serialize_article
from information_retrieval.domain.crawl import CrawlUrl
from information_retrieval.domain.errors import ArticleParseError


class ImportManualArticle:
    def __init__(
        self,
        repository: CrawlUrlRepository,
        storage: ArticleFileStorage,
    ) -> None:
        """Reuse crawler persistence so manual and fetched sources create identical artifacts."""
        self._repository = repository
        self._storage = storage

    def execute(self, blocks: list[ContentBlock]) -> CrawlUrl:
        """Reserve the database docid before serializing metadata that must reference that id."""
        title = blocks[0].text
        row = self._repository.insert_manual_pending(title)
        try:
            serialized = serialize_article(row.id, blocks)
            file_path = self._storage.write(row.id, serialized)
        except (ArticleParseError, OSError) as error:
            self._repository.mark_failed(row.id, str(error))
            raise
        return self._repository.mark_completed(row.id, file_path)
