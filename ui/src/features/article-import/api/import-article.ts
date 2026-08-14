import type {
  ArticleImportDraft,
  ManualArticleBlock,
} from "@/features/article-import/model/article-import";
import { API_ENDPOINTS } from "@/shared/api/endpoints";
import { requestJson } from "@/shared/api/http-client";

export interface ImportedArticle {
  id: number;
  url: string;
  status: string;
  file_path: string | null;
}

export interface PreprocessSummary {
  stored_paragraphs: number;
  split_paragraphs: number;
}

export interface SegmentSummary {
  processed_paragraphs: number;
  stored_segments: number;
}

export interface EmbedSummary {
  selected_sentences: number;
  stored_embeddings: number;
}

const JSON_HEADERS = { "Content-Type": "application/json" };

export function importArticle(draft: ArticleImportDraft): Promise<ImportedArticle> {
  // WHY: Both source modes converge on one persisted article id before downstream stages begin.
  const isUrl = draft.kind === "url";
  return requestJson<ImportedArticle>(
    isUrl ? API_ENDPOINTS.crawledArticles : API_ENDPOINTS.manualArticle,
    {
      method: "POST",
      headers: JSON_HEADERS,
      body: JSON.stringify(isUrl ? { url: draft.url } : { blocks: draft.blocks }),
    },
  );
}

export function preprocessArticle(articleId: number): Promise<PreprocessSummary> {
  return postStage<PreprocessSummary>(API_ENDPOINTS.preprocessArticle(articleId));
}

export function segmentArticle(articleId: number): Promise<SegmentSummary> {
  return postStage<SegmentSummary>(API_ENDPOINTS.segmentArticle(articleId));
}

export function embedArticle(articleId: number): Promise<EmbedSummary> {
  return postStage<EmbedSummary>(API_ENDPOINTS.embedArticle(articleId));
}

function postStage<T>(path: string): Promise<T> {
  // WHY: Stage endpoints intentionally carry identity in the path and require no duplicate body.
  return requestJson<T>(path, { method: "POST" });
}

export type { ManualArticleBlock };
