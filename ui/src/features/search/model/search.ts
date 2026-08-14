export const SEARCH_TOP_K = 10;

export interface SearchArticlesRequest {
  readonly text: string;
  readonly top_k: number;
}

export interface MatchedArticleSentence {
  readonly id: number;
  readonly text: string;
  readonly paragraph_num: number;
  readonly paragraph_part_num: number;
  readonly segment_num: number;
}

export interface RelatedArticle {
  readonly rank: number;
  readonly crawl_url_id: number;
  readonly title: string | null;
  readonly url: string;
  readonly source_kind: "url" | "manual";
  readonly score: number;
  readonly matched_query_sentence: string;
  readonly matched_article_sentence: MatchedArticleSentence;
}

export interface SearchQueryResult {
  readonly segment_count: number;
  readonly segmented_sentences: readonly string[];
}

export interface SearchArticlesResponse {
  readonly status: "success";
  readonly top_k: number;
  readonly returned_count: number;
  readonly query: SearchQueryResult;
  readonly articles: readonly RelatedArticle[];
}
