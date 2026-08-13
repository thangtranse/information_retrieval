import type { ChangeEvent, FormEvent } from "react";
import { ArrowLeft, DatabaseZap, Newspaper } from "lucide-react";
import { Link } from "react-router";

import type { ArticleImportMode } from "@/features/article-import/model/article-import";
import { useArticleImportForm } from "@/features/article-import/model/use-article-import-form";
import { ArticleImportForm } from "@/features/article-import/ui/ArticleImportForm";
import { env } from "@/shared/config/env";
import { useAutoResizeTextarea } from "@/shared/hooks/use-auto-resize-textarea";
import { Button } from "@/shared/ui/button";

export function ArticleImportPage() {
  const importForm = useArticleImportForm(env.articleSourceDomain);
  const contentRef = useAutoResizeTextarea(importForm.content, {
    minRows: 8,
    maxRows: 16,
    enabled: importForm.mode === "content",
  });

  const handleModeChange = (mode: ArticleImportMode) => {
    importForm.changeMode(mode);
  };

  const handleUrlChange = (event: ChangeEvent<HTMLInputElement>) => {
    importForm.updateUrl(event.target.value);
  };

  const handleContentChange = (event: ChangeEvent<HTMLTextAreaElement>) => {
    importForm.updateContent(event.target.value);
  };

  const handleUrlBlur = () => {
    importForm.blurUrl();
  };

  const handleContentBlur = () => {
    importForm.blurContent();
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    // WHY: The page owns submission policy so the form remains a reusable presentational component.
    event.preventDefault();
    importForm.submit();
  };

  return (
    <main className="relative min-h-svh overflow-hidden bg-linear-to-b from-neutral-50 via-white to-neutral-100 px-4 py-8 sm:py-14">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 top-0 -z-0 h-80 bg-[radial-gradient(circle_at_top,rgba(163,163,163,0.18),transparent_68%)]"
      />
      <div className="relative z-10 mx-auto flex w-full max-w-3xl flex-col gap-8">
        <nav aria-label="Điều hướng bài viết" className="flex flex-wrap items-center gap-2">
          <Button asChild className="w-fit" variant="ghost">
            <Link to="/">
              <ArrowLeft aria-hidden="true" />
              Quay lại tìm kiếm
            </Link>
          </Button>
          <Button asChild className="w-fit" variant="ghost">
            <Link to="/articles/crawled">
              <Newspaper aria-hidden="true" />
              Bài viết đã crawl
            </Link>
          </Button>
        </nav>

        <header className="mx-auto max-w-2xl space-y-5 text-center">
          <div className="space-y-3">
            <p className="inline-flex items-center gap-2 text-sm font-medium tracking-[0.16em] text-muted-foreground uppercase">
              <DatabaseZap aria-hidden="true" className="size-4" />
              Nguồn dữ liệu
            </p>
            <p className="mx-auto max-w-xl text-base leading-7 text-muted-foreground sm:text-lg">
              Cung cấp liên kết để crawl hoặc dán nội dung bài báo để chuẩn bị cho pipeline tìm
              kiếm.
            </p>
          </div>
        </header>

        <ArticleImportForm
          canSubmit={importForm.canSubmit}
          content={importForm.content}
          contentError={importForm.contentError}
          contentRef={contentRef}
          mode={importForm.mode}
          onContentBlur={handleContentBlur}
          onContentChange={handleContentChange}
          onModeChange={handleModeChange}
          onSubmit={handleSubmit}
          onUrlBlur={handleUrlBlur}
          onUrlChange={handleUrlChange}
          sourceDomain={env.articleSourceDomain}
          submittedDraft={importForm.submittedDraft}
          url={importForm.url}
          urlError={importForm.urlError}
        />
      </div>
    </main>
  );
}
