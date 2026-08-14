import { useQuery } from "@tanstack/react-query";

import { getArticlePreview } from "@/features/article-list/api/get-article-preview";
import { articleListQueryKeys } from "@/features/article-list/model/article-list";

const PREVIEW_CACHE_TIME_MS = 10 * 60 * 1000;

export function useArticlePreview(articleId: number, enabled = true) {
  // WHY: Visible cards reuse metadata for the session, while inactive entries expire to cap RAM.
  return useQuery({
    queryKey: articleListQueryKeys.preview(articleId),
    queryFn: ({ signal }) => getArticlePreview(articleId, signal),
    staleTime: Infinity,
    gcTime: PREVIEW_CACHE_TIME_MS,
    retry: 1,
    enabled,
  });
}
