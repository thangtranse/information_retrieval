import { ArrowLeft, Newspaper, RefreshCcw } from "lucide-react";
import { Link } from "react-router";

import { useCrawledArticles } from "@/features/article-list/model/use-crawled-articles";
import { CrawledArticleList } from "@/features/article-list/ui/CrawledArticleList";
import { Button } from "@/shared/ui/button";
import { Card, CardContent } from "@/shared/ui/card";
import { Skeleton } from "@/shared/ui/skeleton";

function InitialLoadingState() {
  return (
    <div aria-label="Đang tải danh sách bài viết" className="space-y-6">
      {[0, 1].map((item) => (
        <Card className="gap-4 bg-white p-0" key={item}>
          <Skeleton className="h-52 rounded-none sm:h-60" />
          <CardContent className="space-y-3 pb-6">
            <Skeleton className="h-6 w-4/5" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-2/3" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export function CrawledArticlePage() {
  const articleQuery = useCrawledArticles();
  const articles = articleQuery.data?.pages.flatMap((page) => page.items) ?? [];

  const loadNextPage = () => {
    // WHY: Manual and intersection-driven loading can meet in the same render frame; keeping the
    // active request prevents TanStack Query from aborting and repeating the same cursor.
    void articleQuery.fetchNextPage({ cancelRefetch: false });
  };

  return (
    <main className="min-h-svh bg-linear-to-b from-neutral-50 via-white to-neutral-100 px-4 py-8 sm:py-14">
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-8">
        <Button asChild className="w-fit" variant="ghost">
          <Link to="/">
            <ArrowLeft aria-hidden="true" />
            Quay lại tìm kiếm
          </Link>
        </Button>

        <header className="space-y-4">
          <div className="space-y-2">
            <p className="text-sm font-medium tracking-[0.16em] text-muted-foreground uppercase">
              Kho dữ liệu
            </p>
            <h1 className="font-heading text-4xl font-semibold tracking-tight sm:text-5xl">
              Bài viết đã crawl
            </h1>
            <p className="max-w-2xl text-base leading-7 text-muted-foreground sm:text-lg">
              Duyệt các bài viết mới cập nhật cùng nội dung xem trước từ trang nguồn.
            </p>
          </div>
        </header>

        {articleQuery.isPending ? <InitialLoadingState /> : null}

        {articleQuery.isError && articles.length === 0 ? (
          <Card className="bg-white text-center">
            <CardContent className="space-y-4 py-8">
              <p role="alert">Không thể tải danh sách bài viết.</p>
              <Button onClick={() => articleQuery.refetch()} type="button" variant="outline">
                <RefreshCcw aria-hidden="true" />
                Thử lại
              </Button>
            </CardContent>
          </Card>
        ) : null}

        {!articleQuery.isPending && !articleQuery.isError && articles.length === 0 ? (
          <Card className="bg-white text-center">
            <CardContent className="py-10 text-muted-foreground">
              Chưa có bài viết nào được crawl thành công.
            </CardContent>
          </Card>
        ) : null}

        {articles.length > 0 ? (
          <CrawledArticleList
            articles={articles}
            fetchNextPage={loadNextPage}
            hasNextPage={articleQuery.hasNextPage}
            isFetching={articleQuery.isFetching}
            isFetchingNextPage={articleQuery.isFetchingNextPage}
            nextPageFailed={articleQuery.isFetchNextPageError}
          />
        ) : null}
      </div>
    </main>
  );
}
