import type { ArticlePreview } from "@/features/article-list/model/article-list";
import { API_ENDPOINTS } from "@/shared/api/endpoints";
import { requestJson } from "@/shared/api/http-client";

export function getArticlePreview(
  articleId: number,
  signal?: AbortSignal,
): Promise<ArticlePreview> {
  // WHY: Preview transport stays feature-owned while sharing the global status/error boundary.
  return requestJson<ArticlePreview>(API_ENDPOINTS.articlePreview(articleId), { signal });
}
