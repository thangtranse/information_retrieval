export interface CrawledArticle {
  id: number;
  url: string;
  source_kind: "url" | "manual";
  display_title: string | null;
  updated_at: string;
}

export interface CrawledArticlePage {
  items: CrawledArticle[];
  next_cursor: string | null;
}

export interface ArticlePreview {
  title: string | null;
  description: string | null;
  image_url: string | null;
  site_name: string | null;
}

export const ARTICLE_PAGE_LIMIT = 5;

export const articleListQueryKeys = {
  all: ["crawled-articles"] as const,
  preview: (articleId: number) => ["crawled-articles", "preview", articleId] as const,
};
