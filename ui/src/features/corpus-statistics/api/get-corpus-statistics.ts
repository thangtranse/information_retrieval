import type {
  CorpusStatistics,
  TopWordsLimit,
} from "@/features/corpus-statistics/model/corpus-statistics";
import { API_ENDPOINTS } from "@/shared/api/endpoints";
import { requestJson } from "@/shared/api/http-client";

export function getCorpusStatistics(
  topWordsLimit: TopWordsLimit,
  signal?: AbortSignal,
): Promise<CorpusStatistics> {
  /** WHY: Abort propagation prevents obsolete limit selections from consuming browser connections. */
  return requestJson<CorpusStatistics>(API_ENDPOINTS.corpusStatistics(topWordsLimit), { signal });
}
