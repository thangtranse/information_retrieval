import type { CrawledArticlePage } from "@/features/article-list/model/article-list";
import { ARTICLE_PAGE_LIMIT } from "@/features/article-list/model/article-list";
import { API_ENDPOINTS } from "@/shared/api/endpoints";
import { requestJson } from "@/shared/api/http-client";

export function getCrawledArticles(
  cursor: string | null,
  signal?: AbortSignal,
): Promise<CrawledArticlePage> {
  // WHY: URLSearchParams prevents opaque cursor characters from changing query semantics.
  const query = new URLSearchParams({ limit: String(ARTICLE_PAGE_LIMIT) });
  if (cursor) query.set("cursor", cursor);
  return requestJson<CrawledArticlePage>(`${API_ENDPOINTS.crawledArticles}?${query}`, { signal });
}
