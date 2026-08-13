import { useQuery } from "@tanstack/react-query";

import { getCorpusStatistics } from "@/features/corpus-statistics/api/get-corpus-statistics";
import {
  corpusStatisticsQueryKeys,
  type TopWordsLimit,
} from "@/features/corpus-statistics/model/corpus-statistics";

export function useCorpusStatistics(topWordsLimit: TopWordsLimit) {
  /** WHY: Limit-specific keys preserve useful cached rankings when users compare list sizes. */
  return useQuery({
    queryKey: corpusStatisticsQueryKeys.byTopWordsLimit(topWordsLimit),
    queryFn: ({ signal }) => getCorpusStatistics(topWordsLimit, signal),
    placeholderData: (previousData) => previousData,
  });
}
