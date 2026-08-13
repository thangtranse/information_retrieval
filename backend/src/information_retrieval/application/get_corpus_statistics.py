from information_retrieval.application.corpus_ports import CorpusStatisticsRepository
from information_retrieval.domain.corpus import CorpusStatistics


class GetCorpusStatistics:
    def __init__(self, repository: CorpusStatisticsRepository) -> None:
        self._repository = repository

    def execute(self, top_words_limit: int) -> CorpusStatistics:
        """Keep the HTTP layer independent from the corpus persistence implementation."""
        return self._repository.get_statistics(top_words_limit)
