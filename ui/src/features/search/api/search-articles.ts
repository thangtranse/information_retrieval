import type { SearchArticlesRequest, SearchArticlesResponse } from "@/features/search/model/search";
import { API_ENDPOINTS } from "@/shared/api/endpoints";
import { requestJson } from "@/shared/api/http-client";

export function searchArticles(request: SearchArticlesRequest): Promise<SearchArticlesResponse> {
  // WHY: Keeping serialization at the feature boundary prevents UI components from depending on HTTP details.
  return requestJson<SearchArticlesResponse>(API_ENDPOINTS.searchArticles, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
}
