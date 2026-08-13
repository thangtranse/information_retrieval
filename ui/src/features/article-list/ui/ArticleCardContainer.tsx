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
  const previewQuery = useArticlePreview(article.id);

  return (
    <ArticleCard
      article={article}
      isPreviewLoading={previewQuery.isPending}
      preview={previewQuery.data}
      previewFailed={previewQuery.isError}
      titleId={titleId}
    />
  );
}
