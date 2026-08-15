import { ExternalLink, FileSearch2, Quote } from "lucide-react";

import type { SearchArticlesResponse } from "@/features/search/model/search";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/shared/ui/card";

interface SearchResultsProps {
  result: SearchArticlesResponse;
}

const scoreFormatter = new Intl.NumberFormat("vi-VN", {
  style: "percent",
  maximumFractionDigits: 2,
});

function getHostname(url: string): string {
  // WHY: The source hostname remains scannable while the complete destination stays on the link.
  try {
    return new URL(url).hostname;
  } catch {
    return url;
  }
}

export function SearchResults({ result }: SearchResultsProps) {
  return (
    <section aria-labelledby="search-results-title" className="space-y-5">
      <div
        aria-live="polite"
        className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between"
        role="status"
      >
        <div>
          <p className="text-sm font-medium tracking-[0.12em] text-muted-foreground uppercase">
            Kết quả liên quan
          </p>
          <h2 className="font-heading text-2xl font-semibold" id="search-results-title">
            {result.returned_count} bài viết
          </h2>
        </div>
        <p className="text-sm text-muted-foreground">
          Truy vấn được phân thành {result.query.segment_count} câu
        </p>
      </div>

      {result.returned_count === 0 ? (
        <Card className="border-0 bg-white text-center shadow-lg shadow-black/5">
          <CardContent className="space-y-3 py-10">
            <FileSearch2 aria-hidden="true" className="mx-auto size-8 text-muted-foreground" />
            <p className="font-medium">Chưa tìm thấy bài viết liên quan.</p>
            <p className="text-sm text-muted-foreground">Hãy thử diễn đạt lại nội dung tìm kiếm.</p>
          </CardContent>
        </Card>
      ) : null}

      <div className="space-y-4">
        {result.articles.map((article) => {
          const isManual = article.source_kind === "manual";
          const hostname = isManual ? "Nhập thủ công" : getHostname(article.url);
          const titleId = `search-result-title-${article.crawl_url_id}`;

          return (
            <article aria-labelledby={titleId} key={article.crawl_url_id}>
              <Card className="gap-4 border-0 bg-white shadow-lg shadow-black/5 ring-black/8">
                <CardHeader className="gap-3 sm:grid-cols-[auto_1fr_auto]">
                  <span className="flex size-9 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground">
                    {article.rank}
                  </span>
                  <div className="min-w-0 space-y-1">
                    <CardTitle
                      aria-level={3}
                      className="text-lg leading-6 sm:text-xl"
                      id={titleId}
                      role="heading"
                    >
                      {article.title ?? `Bài viết #${article.crawl_url_id}`}
                    </CardTitle>
                    <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted-foreground">
                      <span className="truncate">{hostname}</span>
                      <span aria-hidden="true">·</span>
                      <span className="tabular-nums">ID bài viết: {article.crawl_url_id}</span>
                    </div>
                  </div>
                  <span className="w-fit rounded-full bg-neutral-100 px-3 py-1 text-xs font-semibold tabular-nums">
                    {scoreFormatter.format(article.score)} tương đồng
                  </span>
                </CardHeader>

                <CardContent className="grid gap-3 sm:grid-cols-2">
                  <blockquote className="rounded-lg bg-neutral-50 p-4">
                    <div className="mb-2 flex items-center gap-2 text-xs font-medium tracking-wide text-muted-foreground uppercase">
                      <Quote aria-hidden="true" className="size-3.5" />
                      Câu truy vấn khớp
                    </div>
                    <p className="leading-6">{article.matched_query_sentence}</p>
                  </blockquote>
                  <blockquote className="rounded-lg bg-neutral-50 p-4">
                    <div className="mb-2 flex items-center gap-2 text-xs font-medium tracking-wide text-muted-foreground uppercase">
                      <Quote aria-hidden="true" className="size-3.5" />
                      Câu trong bài viết
                    </div>
                    <p className="leading-6">{article.matched_article_sentence.text}</p>
                  </blockquote>
                </CardContent>

                <CardFooter className="flex flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <span className="text-xs text-muted-foreground">
                    Đoạn {article.matched_article_sentence.paragraph_num}, phần{" "}
                    {article.matched_article_sentence.paragraph_part_num}, câu{" "}
                    {article.matched_article_sentence.segment_num}
                  </span>
                  {!isManual ? (
                    <a
                      className="inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-neutral-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      href={article.url}
                      rel="noopener noreferrer"
                      target="_blank"
                    >
                      Mở bài viết
                      <ExternalLink aria-hidden="true" className="size-4" />
                    </a>
                  ) : null}
                </CardFooter>
              </Card>
            </article>
          );
        })}
      </div>
    </section>
  );
}
