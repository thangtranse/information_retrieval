import type { CrawledArticle } from "@/features/article-list/model/article-list";
import { useArticlePreview } from "@/features/article-list/model/use-article-preview";
import { ArticleCard } from "@/features/article-list/ui/ArticleCard";

export function ArticleCardContainer({
  article,
  titleId,
}: {
  article: CrawledArticle;
  titleId: string;
}) {
  const previewEnabled = article.source_kind === "url";
  const previewQuery = useArticlePreview(article.id, previewEnabled);

  return (
    <ArticleCard
      article={article}
      isPreviewLoading={previewEnabled && previewQuery.isPending}
      preview={previewQuery.data}
      previewFailed={previewQuery.isError}
      titleId={titleId}
    />
  );
}
