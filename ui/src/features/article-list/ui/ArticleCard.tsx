import { useState } from "react";
import { CalendarClock, ExternalLink, FileText, Link2 } from "lucide-react";

import type { ArticlePreview, CrawledArticle } from "@/features/article-list/model/article-list";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/shared/ui/card";
import { Skeleton } from "@/shared/ui/skeleton";

interface ArticleCardProps {
  article: CrawledArticle;
  preview: ArticlePreview | undefined;
  isPreviewLoading: boolean;
  previewFailed: boolean;
  titleId: string;
}

const dateFormatter = new Intl.DateTimeFormat("vi-VN", {
  dateStyle: "medium",
  timeStyle: "short",
});

function getHostname(url: string): string {
  // WHY: A compact host label is easier to scan than repeating the complete article URL.
  try {
    return new URL(url).hostname;
  } catch {
    return url;
  }
}

function PreviewImage({ imageUrl }: { imageUrl: string }) {
  const [isVisible, setIsVisible] = useState(true);
  if (!isVisible) return null;

  return (
    <img
      alt=""
      className="h-52 w-full bg-neutral-100 object-cover sm:h-60"
      decoding="async"
      loading="lazy"
      onError={() => setIsVisible(false)}
      referrerPolicy="no-referrer"
      src={imageUrl}
    />
  );
}

export function ArticleCard({
  article,
  preview,
  isPreviewLoading,
  previewFailed,
  titleId,
}: ArticleCardProps) {
  const isManual = article.source_kind === "manual";
  const hostname = isManual ? "Nhập thủ công" : getHostname(article.url);
  const title = article.display_title ?? preview?.title ?? hostname;

  return (
    <Card className="gap-0 border-0 bg-white py-0 shadow-lg shadow-black/5 ring-black/8 transition-shadow hover:shadow-xl">
      {isPreviewLoading ? <Skeleton className="h-52 w-full rounded-none sm:h-60" /> : null}
      {!isPreviewLoading && preview?.image_url ? (
        <PreviewImage key={preview.image_url} imageUrl={preview.image_url} />
      ) : null}

      <CardHeader className="gap-3 py-5">
        <div className="flex items-center gap-2 text-xs font-medium tracking-wide text-muted-foreground uppercase">
          {isManual ? (
            <FileText aria-hidden="true" className="size-3.5" />
          ) : (
            <Link2 aria-hidden="true" className="size-3.5" />
          )}
          {preview?.site_name ?? hostname}
        </div>
        {isPreviewLoading ? (
          <div className="space-y-2">
            <CardTitle aria-level={2} className="sr-only" id={titleId} role="heading">
              {hostname}
            </CardTitle>
            <div aria-label="Đang tải nội dung xem trước">
              <Skeleton className="h-6 w-4/5" />
              <Skeleton className="h-6 w-3/5" />
            </div>
          </div>
        ) : (
          <CardTitle
            aria-level={2}
            className="text-xl leading-7 sm:text-2xl"
            id={titleId}
            role="heading"
          >
            {title}
          </CardTitle>
        )}
      </CardHeader>

      <CardContent className="pb-5">
        {isPreviewLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-11/12" />
            <Skeleton className="h-4 w-2/3" />
          </div>
        ) : preview?.description ? (
          <p className="line-clamp-3 text-sm leading-6 text-muted-foreground sm:text-base">
            {preview.description}
          </p>
        ) : (
          <p className="text-sm leading-6 text-muted-foreground">
            {isManual
              ? "Nội dung được nhập trực tiếp vào kho dữ liệu."
              : previewFailed
                ? "Không thể tải nội dung xem trước. Bạn vẫn có thể mở bài viết nguồn."
                : "Bài viết chưa cung cấp mô tả xem trước."}
          </p>
        )}
      </CardContent>

      <CardFooter className="flex flex-col items-stretch gap-3 border-t sm:flex-row sm:items-center sm:justify-between">
        <span className="inline-flex items-center gap-2 text-xs text-muted-foreground">
          <CalendarClock aria-hidden="true" className="size-3.5" />
          Cập nhật {dateFormatter.format(new Date(article.updated_at))}
        </span>
        {!isManual ? (
          <a
            className="inline-flex items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-neutral-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
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
  );
}
