import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import {
  embedArticle,
  importArticle,
  preprocessArticle,
  segmentArticle,
} from "@/features/article-import/api/import-article";
import type { ArticleImportDraft } from "@/features/article-import/model/article-import";
import { articleListQueryKeys } from "@/features/article-list/model/article-list";
import { corpusStatisticsQueryKeys } from "@/features/corpus-statistics/model/corpus-statistics";

export type ImportStageId = "source" | "storage" | "preprocess" | "segment" | "embed";
export type ImportStageStatus = "pending" | "active" | "completed" | "failed";

export interface ImportStage {
  id: ImportStageId;
  label: string;
  status: ImportStageStatus;
  detail?: string;
}

const INITIAL_STAGES: ImportStage[] = [
  { id: "source", label: "Nhận nguồn", status: "pending" },
  { id: "storage", label: "Lưu bài", status: "pending" },
  { id: "preprocess", label: "Preprocess", status: "pending" },
  { id: "segment", label: "Segment", status: "pending" },
  { id: "embed", label: "Embedding", status: "pending" },
];

export function useArticleImportPipeline() {
  const queryClient = useQueryClient();
  const [stages, setStages] = useState<ImportStage[]>(INITIAL_STAGES);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async (draft: ArticleImportDraft) => {
    // WHY: One ordered controller prevents a later stage from running against stale prerequisites.
    if (isRunning) return;
    setIsRunning(true);
    setError(null);
    setStages(
      INITIAL_STAGES.map((stage) =>
        stage.id === "source" ? { ...stage, status: "completed", detail: "Dữ liệu hợp lệ" } : stage,
      ),
    );

    try {
      updateStage(setStages, "storage", "active");
      const article = await importArticle(draft);
      updateStage(setStages, "storage", "completed", `Đã lưu bài #${article.id}`);

      updateStage(setStages, "preprocess", "active");
      const preprocessed = await preprocessArticle(article.id);
      updateStage(
        setStages,
        "preprocess",
        "completed",
        `${preprocessed.stored_paragraphs} đoạn đã chuẩn hóa`,
      );

      updateStage(setStages, "segment", "active");
      const segmented = await segmentArticle(article.id);
      updateStage(
        setStages,
        "segment",
        "completed",
        `${segmented.stored_segments} câu đã phân đoạn`,
      );

      updateStage(setStages, "embed", "active");
      const embedded = await embedArticle(article.id);
      updateStage(setStages, "embed", "completed", `${embedded.stored_embeddings} vector đã lưu`);

      await Promise.all([
        queryClient.invalidateQueries({ queryKey: articleListQueryKeys.all }),
        queryClient.invalidateQueries({ queryKey: corpusStatisticsQueryKeys.all }),
      ]);
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "Không thể xử lý bài viết.";
      setError(message);
      setStages((current) =>
        current.map((stage) =>
          stage.status === "active" ? { ...stage, status: "failed", detail: message } : stage,
        ),
      );
    } finally {
      setIsRunning(false);
    }
  };

  return { stages, isRunning, error, run };
}

function updateStage(
  setStages: React.Dispatch<React.SetStateAction<ImportStage[]>>,
  id: ImportStageId,
  status: ImportStageStatus,
  detail?: string,
) {
  // WHY: Immutable focused updates keep completed evidence visible while the next request runs.
  setStages((current) =>
    current.map((stage) => (stage.id === id ? { ...stage, status, detail } : stage)),
  );
}
