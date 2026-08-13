from typing import Protocol

from information_retrieval.domain.corpus import CorpusStatistics


class CorpusStatisticsRepository(Protocol):
    def get_statistics(self, top_words_limit: int) -> CorpusStatistics:
        """Return statistics only from complete normalized/segmented document snapshots."""
        ...
