export const API_ENDPOINTS = {
  health: "/api/v1/health",
  crawledArticles: "/api/v1/crawler/articles",
  articlePreview: (articleId: number) => `/api/v1/crawler/articles/${articleId}/preview`,
} as const;
