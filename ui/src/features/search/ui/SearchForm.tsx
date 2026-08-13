import type { ChangeEventHandler, FormEventHandler, KeyboardEventHandler, RefObject } from "react";
import { Search } from "lucide-react";

import { Button } from "@/shared/ui/button";
import { Card, CardContent } from "@/shared/ui/card";
import { Textarea } from "@/shared/ui/textarea";

interface SearchFormProps {
  query: string;
  canSubmit: boolean;
  textareaRef: RefObject<HTMLTextAreaElement | null>;
  onQueryChange: ChangeEventHandler<HTMLTextAreaElement>;
  onKeyDown: KeyboardEventHandler<HTMLTextAreaElement>;
  onSubmit: FormEventHandler<HTMLFormElement>;
}

export function SearchForm({
  query,
  canSubmit,
  textareaRef,
  onQueryChange,
  onKeyDown,
  onSubmit,
}: SearchFormProps) {
  return (
    <Card className="border-0 bg-white/90 shadow-xl shadow-black/5 ring-1 ring-black/5 backdrop-blur">
      <CardContent className="p-4 sm:p-6">
        <form className="space-y-5" onSubmit={onSubmit}>
          <div className="space-y-2.5">
            <label className="text-sm font-medium" htmlFor="search-query">
              Nội dung tìm kiếm
            </label>
            <Textarea
              aria-describedby="search-query-help"
              className="min-h-0 resize-none [field-sizing:fixed] px-4 py-3 text-base leading-6 shadow-none md:text-base"
              id="search-query"
              onChange={onQueryChange}
              onKeyDown={onKeyDown}
              placeholder="Nhập nội dung bạn muốn tìm kiếm…"
              ref={textareaRef}
              rows={3}
              value={query}
            />
          </div>

          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-xs leading-5 text-muted-foreground" id="search-query-help">
              Enter để xuống dòng · Ctrl/⌘ + Enter để tìm kiếm
            </p>
            <Button
              className="h-10 w-full px-5 sm:w-auto"
              disabled={!canSubmit}
              size="lg"
              type="submit"
            >
              <Search aria-hidden="true" />
              Tìm kiếm
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
