import { useMutation } from "@tanstack/react-query";

import { searchArticles } from "@/features/search/api/search-articles";

export function useArticleSearch() {
  // WHY: Search is an explicit user command, so mutation state models one request without cache-driven refetches.
  return useMutation({ mutationFn: searchArticles });
}
