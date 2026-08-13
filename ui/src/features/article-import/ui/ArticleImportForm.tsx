import type { ChangeEventHandler, FocusEventHandler, FormEventHandler, RefObject } from "react";
import { CircleCheck, FileText, Link2, ShieldCheck } from "lucide-react";

import type {
  ArticleImportDraft,
  ArticleImportMode,
  ArticleUrlError,
} from "@/features/article-import/model/article-import";
import { Button } from "@/shared/ui/button";
import { Card, CardContent } from "@/shared/ui/card";
import { Input } from "@/shared/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/shared/ui/tabs";
import { Textarea } from "@/shared/ui/textarea";

interface ArticleImportFormProps {
  mode: ArticleImportMode;
  url: string;
  content: string;
  sourceDomain: string;
  urlError: ArticleUrlError | null;
  contentError: boolean;
  canSubmit: boolean;
  submittedDraft: ArticleImportDraft | null;
  contentRef: RefObject<HTMLTextAreaElement | null>;
  onModeChange: (mode: ArticleImportMode) => void;
  onUrlChange: ChangeEventHandler<HTMLInputElement>;
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
  sourceDomain,
  urlError,
  contentError,
  canSubmit,
  submittedDraft,
  contentRef,
  onModeChange,
  onUrlChange,
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
              <label className="text-sm font-medium" htmlFor="article-content">
                Nội dung bài báo
              </label>
              <Textarea
                aria-describedby={contentError ? "article-content-error" : "article-content-help"}
                aria-invalid={contentError}
                className="min-h-0 resize-none [field-sizing:fixed] px-4 py-3 text-base leading-6 shadow-none md:text-base"
                id="article-content"
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
                  Nội dung sẽ được chuẩn hóa và lưu trữ khi API được tích hợp.
                </p>
              )}
            </TabsContent>
          </Tabs>

          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-xs leading-5 text-muted-foreground">
              Phiên bản hiện tại chỉ kiểm tra dữ liệu, chưa gửi lên hệ thống.
            </p>
            <Button
              className="h-10 w-full px-5 sm:w-auto"
              disabled={!canSubmit}
              size="lg"
              type="submit"
            >
              <ShieldCheck aria-hidden="true" />
              Kiểm tra dữ liệu
            </Button>
          </div>

          {submittedDraft ? (
            <div
              className="flex items-start gap-2 rounded-lg bg-emerald-50 px-4 py-3 text-sm text-emerald-800 ring-1 ring-emerald-200"
              data-import-kind={submittedDraft.kind}
              role="status"
            >
              <CircleCheck aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
              Dữ liệu hợp lệ, sẵn sàng gửi khi API được tích hợp.
            </div>
          ) : null}
        </form>
      </CardContent>
    </Card>
  );
}
