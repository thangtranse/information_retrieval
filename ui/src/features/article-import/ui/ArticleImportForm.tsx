import type { ChangeEventHandler, FocusEventHandler, FormEventHandler, RefObject } from "react";
import { FileText, Link2, LoaderCircle, Play, ShieldCheck } from "lucide-react";

import type {
  ArticleImportMode,
  ArticleUrlError,
} from "@/features/article-import/model/article-import";
import type { ImportStage } from "@/features/article-import/model/use-article-import-pipeline";
import { ArticleImportProgress } from "@/features/article-import/ui/ArticleImportProgress";
import { Button } from "@/shared/ui/button";
import { Card, CardContent } from "@/shared/ui/card";
import { Input } from "@/shared/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/shared/ui/tabs";
import { Textarea } from "@/shared/ui/textarea";

interface ArticleImportFormProps {
  mode: ArticleImportMode;
  url: string;
  title: string;
  content: string;
  sourceDomain: string;
  urlError: ArticleUrlError | null;
  titleError: boolean;
  contentError: boolean;
  canSubmit: boolean;
  isRunning: boolean;
  stages: ImportStage[];
  contentRef: RefObject<HTMLTextAreaElement | null>;
  onModeChange: (mode: ArticleImportMode) => void;
  onUrlChange: ChangeEventHandler<HTMLInputElement>;
  onTitleChange: ChangeEventHandler<HTMLInputElement>;
  onContentChange: ChangeEventHandler<HTMLTextAreaElement>;
  onUrlBlur: FocusEventHandler<HTMLInputElement>;
  onContentBlur: FocusEventHandler<HTMLTextAreaElement>;
  onSubmit: FormEventHandler<HTMLFormElement>;
}

function getUrlErrorMessage(error: ArticleUrlError, sourceDomain: string): string {
  // WHY: Stable error codes keep validation independent from user-facing Vietnamese copy.
  if (error === "required") return "Vui lòng nhập liên kết bài báo.";
  if (error === "invalid-url") return "Liên kết không hợp lệ. Hãy nhập URL đầy đủ.";
  if (error === "unsupported-protocol") return "Liên kết phải sử dụng giao thức http hoặc https.";
  return `Liên kết phải thuộc ${sourceDomain} hoặc một subdomain của domain này.`;
}

export function ArticleImportForm({
  mode,
  url,
  content,
  title,
  sourceDomain,
  urlError,
  titleError,
  contentError,
  canSubmit,
  isRunning,
  stages,
  contentRef,
  onModeChange,
  onUrlChange,
  onTitleChange,
  onContentChange,
  onUrlBlur,
  onContentBlur,
  onSubmit,
}: ArticleImportFormProps) {
  const handleTabChange = (value: string) => {
    // WHY: Only declared tab values may change the discriminated import mode.
    if (value === "url" || value === "content") onModeChange(value);
  };

  return (
    <Card className="border-0 bg-white/90 shadow-xl shadow-black/5 ring-1 ring-black/5 backdrop-blur">
      <CardContent className="p-4 sm:p-6">
        <form className="space-y-6" noValidate onSubmit={onSubmit}>
          <Tabs onValueChange={handleTabChange} value={mode}>
            <TabsList
              aria-label="Chọn loại dữ liệu bài viết"
              className="grid h-11 w-full grid-cols-2"
            >
              <TabsTrigger className="h-full" value="url">
                <Link2 aria-hidden="true" />
                Liên kết bài báo
              </TabsTrigger>
              <TabsTrigger className="h-full" value="content">
                <FileText aria-hidden="true" />
                Nội dung bài báo
              </TabsTrigger>
            </TabsList>

            <TabsContent className="mt-5 space-y-2.5" value="url">
              <label className="text-sm font-medium" htmlFor="article-url">
                Liên kết nguồn
              </label>
              <Input
                aria-describedby={urlError ? "article-url-error" : "article-url-help"}
                aria-invalid={Boolean(urlError)}
                className="h-11 px-3 text-base md:text-base"
                id="article-url"
                inputMode="url"
                onBlur={onUrlBlur}
                onChange={onUrlChange}
                disabled={isRunning}
                placeholder={`https://${sourceDomain}/...`}
                type="url"
                value={url}
              />
              {urlError ? (
                <p className="text-sm text-destructive" id="article-url-error" role="alert">
                  {getUrlErrorMessage(urlError, sourceDomain)}
                </p>
              ) : (
                <p
                  className="flex items-center gap-1.5 text-xs leading-5 text-muted-foreground"
                  id="article-url-help"
                >
                  <ShieldCheck aria-hidden="true" className="size-3.5" />
                  Chấp nhận {sourceDomain} và các subdomain. Tham số và fragment sẽ được loại bỏ.
                </p>
              )}
            </TabsContent>

            <TabsContent className="mt-5 space-y-2.5" value="content">
              <label className="text-sm font-medium" htmlFor="article-title">
                Tiêu đề
              </label>
              <Input
                aria-describedby={titleError ? "article-title-error" : undefined}
                aria-invalid={titleError}
                disabled={isRunning}
                id="article-title"
                onChange={onTitleChange}
                placeholder="Nhập tiêu đề bài viết"
                value={title}
              />
              {titleError ? (
                <p className="text-sm text-destructive" id="article-title-error" role="alert">
                  Vui lòng nhập tiêu đề bài viết.
                </p>
              ) : null}
              <label className="text-sm font-medium" htmlFor="article-content">
                Nội dung bài báo
              </label>
              <Textarea
                aria-describedby={contentError ? "article-content-error" : "article-content-help"}
                aria-invalid={contentError}
                className="min-h-0 resize-none [field-sizing:fixed] px-4 py-3 text-base leading-6 shadow-none md:text-base"
                id="article-content"
                disabled={isRunning}
                onBlur={onContentBlur}
                onChange={onContentChange}
                placeholder="Dán toàn bộ nội dung bài báo tại đây…"
                ref={contentRef}
                rows={8}
                value={content}
              />
              {contentError ? (
                <p className="text-sm text-destructive" id="article-content-error" role="alert">
                  Vui lòng nhập nội dung bài báo.
                </p>
              ) : (
                <p className="text-xs leading-5 text-muted-foreground" id="article-content-help">
                  Mỗi đoạn cách nhau bằng một dòng trống sẽ được lưu thành một block riêng.
                </p>
              )}
            </TabsContent>
          </Tabs>

          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-xs leading-5 text-muted-foreground">
              Bài viết sẽ tự động đi qua preprocess, segment và embedding.
            </p>
            <Button
              className="h-10 w-full px-5 sm:w-auto"
              disabled={!canSubmit || isRunning}
              size="lg"
              type="submit"
            >
              {isRunning ? (
                <LoaderCircle aria-hidden="true" className="animate-spin" />
              ) : (
                <Play aria-hidden="true" />
              )}
              {isRunning ? "Đang xử lý" : "Nhập và xử lý"}
            </Button>
          </div>

          <ArticleImportProgress stages={stages} />
        </form>
      </CardContent>
    </Card>
  );
}
