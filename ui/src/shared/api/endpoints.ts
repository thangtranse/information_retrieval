export const API_ENDPOINTS = {
  health: "/api/v1/health",
  crawledArticles: "/api/v1/crawler/articles",
  manualArticle: "/api/v1/articles/manual",
  preprocessArticle: (articleId: number) => `/api/v1/articles/${articleId}/preprocess`,
  segmentArticle: (articleId: number) => `/api/v1/articles/${articleId}/segment`,
  embedArticle: (articleId: number) => `/api/v1/articles/${articleId}/embed`,
  articlePreview: (articleId: number) => `/api/v1/crawler/articles/${articleId}/preview`,
  searchArticles: "/api/v1/search/articles",
  corpusStatistics: (topWordsLimit: number) =>
    `/api/v1/corpus/statistics?top_words_limit=${topWordsLimit}`,
} as const;
