import type { ChangeEvent, FormEvent, KeyboardEvent } from "react";
import { Activity, FilePlus2, Search } from "lucide-react";
import { Link } from "react-router";

import { useSearchForm } from "@/features/search/model/use-search-form";
import { SearchForm } from "@/features/search/ui/SearchForm";
import { useAutoResizeTextarea } from "@/shared/hooks/use-auto-resize-textarea";

export function SearchPage() {
  const searchForm = useSearchForm();
  const textareaRef = useAutoResizeTextarea(searchForm.query, { minRows: 3, maxRows: 10 });

  const handleQueryChange = (event: ChangeEvent<HTMLTextAreaElement>) => {
    searchForm.updateQuery(event.target.value);
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    // WHY: The page owns submission policy so the form remains a reusable presentational component.
    event.preventDefault();
    searchForm.submit();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    // WHY: A multiline query needs Enter for new lines, so only the explicit modifier shortcut submits.
    if (!(event.ctrlKey || event.metaKey) || event.key !== "Enter") return;

    event.preventDefault();

    if (searchForm.canSubmit) event.currentTarget.form?.requestSubmit();
  };

  return (
    <main className="relative min-h-svh overflow-hidden bg-linear-to-b from-neutral-50 via-white to-neutral-100 px-4 py-10 sm:py-16">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 top-0 -z-0 h-80 bg-[radial-gradient(circle_at_top,rgba(163,163,163,0.18),transparent_68%)]"
      />
      <div className="relative z-10 mx-auto flex w-full max-w-3xl flex-col gap-8 sm:gap-10">
        <header className="mx-auto max-w-2xl space-y-5 text-center">
          <div className="space-y-3">
            <p className="text-sm font-medium tracking-[0.16em] text-muted-foreground uppercase">
              Information Retrieval
            </p>
            <h1 className="font-heading text-4xl font-semibold tracking-tight sm:text-5xl">
              Tìm kiếm thông tin
            </h1>
            <p className="mx-auto max-w-xl text-base leading-7 text-muted-foreground sm:text-lg">
              Nhập nội dung bạn muốn tìm kiếm. Bạn có thể viết nhiều dòng để mô tả rõ nhu cầu.
            </p>
          </div>
        </header>

        <SearchForm
          canSubmit={searchForm.canSubmit}
          onKeyDown={handleKeyDown}
          onQueryChange={handleQueryChange}
          onSubmit={handleSubmit}
          query={searchForm.query}
          textareaRef={textareaRef}
        />

        <nav aria-label="Điều hướng phụ" className="flex flex-wrap justify-center gap-5">
          <Link
            className="inline-flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground focus-visible:rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            to="/articles/import"
          >
            <FilePlus2 aria-hidden="true" className="size-4" />
            Nhập bài viết
          </Link>
          <Link
            className="inline-flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground focus-visible:rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            to="/health-check"
          >
            <Activity aria-hidden="true" className="size-4" />
            Kiểm tra hệ thống
          </Link>
        </nav>
      </div>
    </main>
  );
}
