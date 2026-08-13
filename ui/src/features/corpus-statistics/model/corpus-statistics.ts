export const TOP_WORD_LIMITS = [10, 20, 50, 100] as const;

export type TopWordsLimit = (typeof TOP_WORD_LIMITS)[number];

export interface Distribution {
  min: number | null;
  p25: number | null;
  median: number | null;
  mean: number | null;
  p75: number | null;
  p95: number | null;
  max: number | null;
}

export interface CorpusDistributions {
  word_count: Distribution;
  sentence_count: Distribution;
}

export interface TopWord {
  word: string;
  count: number;
}

export interface SpecialCharacter {
  character: string;
  code_point: string;
  unicode_name: string;
  count: number;
}

export interface CorpusStatistics {
  document_count: number;
  normalized: CorpusDistributions;
  segmented: CorpusDistributions;
  top_words: TopWord[];
  special_characters: SpecialCharacter[];
}

export const corpusStatisticsQueryKeys = {
  all: ["corpus-statistics"] as const,
  byTopWordsLimit: (topWordsLimit: TopWordsLimit) =>
    [...corpusStatisticsQueryKeys.all, topWordsLimit] as const,
};

export function parseTopWordsLimit(value: string | null): TopWordsLimit {
  /** WHY: Normalizing URL input locally prevents invalid requests while preserving shareable state. */
  const parsed = Number(value);
  return TOP_WORD_LIMITS.find((limit) => limit === parsed) ?? 20;
}
