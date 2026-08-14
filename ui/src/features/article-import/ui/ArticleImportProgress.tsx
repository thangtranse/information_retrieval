import { CircleCheck, CircleDashed, CircleX, LoaderCircle } from "lucide-react";

import type { ImportStage } from "@/features/article-import/model/use-article-import-pipeline";

export function ArticleImportProgress({ stages }: { stages: ImportStage[] }) {
  const completed = stages.filter((stage) => stage.status === "completed").length;
  const percentage = (completed / stages.length) * 100;

  return (
    <section aria-label="Tiến độ xử lý bài viết" className="space-y-4" role="status">
      <div className="h-2 overflow-hidden rounded-full bg-neutral-200">
        <div
          className="h-full bg-neutral-950 transition-[width] duration-300"
          style={{ width: `${percentage}%` }}
        />
      </div>
      <ol className="grid gap-3 sm:grid-cols-5">
        {stages.map((stage) => (
          <li className="space-y-1 text-sm" key={stage.id}>
            <span className="flex items-center gap-2 font-medium">
              <StageIcon stage={stage} />
              {stage.label}
            </span>
            {stage.detail ? (
              <span className="block text-xs leading-5 text-muted-foreground">{stage.detail}</span>
            ) : null}
          </li>
        ))}
      </ol>
    </section>
  );
}

function StageIcon({ stage }: { stage: ImportStage }) {
  // WHY: Shape and motion communicate state even when status colors are indistinguishable.
  if (stage.status === "completed") {
    return <CircleCheck aria-hidden="true" className="size-4 text-emerald-600" />;
  }
  if (stage.status === "active") {
    return <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />;
  }
  if (stage.status === "failed") {
    return <CircleX aria-hidden="true" className="size-4 text-destructive" />;
  }
  return <CircleDashed aria-hidden="true" className="size-4 text-muted-foreground" />;
}
