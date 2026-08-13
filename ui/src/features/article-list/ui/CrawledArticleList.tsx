import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { useWindowVirtualizer } from "@tanstack/react-virtual";
import { ChevronsDown, LoaderCircle, RotateCcw } from "lucide-react";

import type { CrawledArticle } from "@/features/article-list/model/article-list";
import { ArticleCardContainer } from "@/features/article-list/ui/ArticleCardContainer";
import { Button } from "@/shared/ui/button";

interface CrawledArticleListProps {
  articles: CrawledArticle[];
  hasNextPage: boolean;
  isFetchingNextPage: boolean;
  isFetching: boolean;
  nextPageFailed: boolean;
  fetchNextPage: () => void;
}

export function CrawledArticleList({
  articles,
  hasNextPage,
  isFetchingNextPage,
  isFetching,
  nextPageFailed,
  fetchNextPage,
}: CrawledArticleListProps) {
  const listRef = useRef<HTMLDivElement>(null);
  const requestedItemCountRef = useRef(-1);
  const [scrollMargin, setScrollMargin] = useState(0);

  useLayoutEffect(() => {
    // WHY: Window virtualization positions rows relative to the page, not only this container.
    const updateMargin = () => setScrollMargin(listRef.current?.offsetTop ?? 0);
    updateMargin();
    window.addEventListener("resize", updateMargin);
    return () => window.removeEventListener("resize", updateMargin);
  }, []);

  const virtualizer = useWindowVirtualizer({
    count: articles.length,
    estimateSize: () => 420,
    overscan: 3,
    scrollMargin,
  });
  const virtualItems = virtualizer.getVirtualItems();
  const lastVirtualIndex = virtualItems.at(-1)?.index;

  useEffect(() => {
    // WHY: Prefetching two rows early hides network latency without requesting every page eagerly.
    if (
      lastVirtualIndex !== undefined &&
      lastVirtualIndex >= articles.length - 2 &&
      hasNextPage &&
      !isFetching &&
      !nextPageFailed &&
      requestedItemCountRef.current !== articles.length
    ) {
      requestedItemCountRef.current = articles.length;
      fetchNextPage();
    }
  }, [
    articles.length,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isFetching,
    lastVirtualIndex,
    nextPageFailed,
  ]);

  return (
    <div ref={listRef}>
      <div
        aria-busy={isFetchingNextPage}
        className="relative w-full"
        id="crawled-article-list"
        role="feed"
        style={{ height: virtualizer.getTotalSize() }}
      >
        {virtualItems.map((virtualItem) => {
          const article = articles[virtualItem.index];
          const titleId = `crawled-article-title-${article.id}`;
          return (
            <article
              aria-labelledby={titleId}
              aria-posinset={virtualItem.index + 1}
              aria-setsize={-1}
              className="absolute top-0 left-0 w-full pb-6"
              data-index={virtualItem.index}
              key={article.id}
              ref={virtualizer.measureElement}
              style={{ transform: `translateY(${virtualItem.start - scrollMargin}px)` }}
            >
              <ArticleCardContainer article={article} titleId={titleId} />
            </article>
          );
        })}
      </div>

      <div aria-live="polite" className="flex min-h-16 items-center justify-center py-3">
        {isFetchingNextPage ? (
          <p className="inline-flex items-center gap-2 text-sm text-muted-foreground">
            <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />
            Đang tải thêm bài viết…
          </p>
        ) : null}
        {hasNextPage && !isFetchingNextPage ? (
          <Button
            aria-controls="crawled-article-list"
            disabled={isFetching}
            onClick={fetchNextPage}
            type="button"
            variant="outline"
          >
            {nextPageFailed ? (
              <RotateCcw aria-hidden="true" />
            ) : (
              <ChevronsDown aria-hidden="true" />
            )}
            {nextPageFailed ? "Thử tải lại" : "Tải thêm bài viết"}
          </Button>
        ) : null}
        {!hasNextPage && !nextPageFailed ? (
          <p className="text-sm text-muted-foreground">Bạn đã xem hết danh sách.</p>
        ) : null}
      </div>
    </div>
  );
}
