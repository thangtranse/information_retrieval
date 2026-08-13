export const API_ENDPOINTS = {
  health: "/api/v1/health",
  crawledArticles: "/api/v1/crawler/articles",
  articlePreview: (articleId: number) => `/api/v1/crawler/articles/${articleId}/preview`,
  searchArticles: "/api/v1/search/articles",
  corpusStatistics: (topWordsLimit: number) =>
    `/api/v1/corpus/statistics?top_words_limit=${topWordsLimit}`,
} as const;
