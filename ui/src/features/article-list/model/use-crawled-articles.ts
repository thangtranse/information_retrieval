import { useInfiniteQuery } from "@tanstack/react-query";

import { getCrawledArticles } from "@/features/article-list/api/get-crawled-articles";
import { articleListQueryKeys } from "@/features/article-list/model/article-list";

export function useCrawledArticles() {
  // WHY: The server-owned opaque cursor prevents UI pagination from coupling to database order.
  return useInfiniteQuery({
    queryKey: articleListQueryKeys.all,
    initialPageParam: null as string | null,
    queryFn: ({ pageParam, signal }) => getCrawledArticles(pageParam, signal),
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
  });
}
