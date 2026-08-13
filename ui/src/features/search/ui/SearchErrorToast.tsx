import { useEffect } from "react";
import { CircleAlert, X } from "lucide-react";

import { ApiRequestError } from "@/shared/api/http-client";
import { Button } from "@/shared/ui/button";

interface SearchErrorToastProps {
  error: Error;
  onDismiss: () => void;
}

const AUTO_DISMISS_MS = 6_000;

function getErrorMessage(error: Error): string {
  // WHY: Status-based copy helps recovery without exposing backend diagnostics in the browser.
  if (error instanceof ApiRequestError && error.status === 422) {
    return "Nội dung tìm kiếm không hợp lệ. Hãy kiểm tra và thử lại.";
  }
  if (error instanceof ApiRequestError && error.status === 503) {
    return "Dịch vụ tìm kiếm đang tạm thời không khả dụng. Vui lòng thử lại sau.";
  }
  return "Không thể tìm kiếm bài viết. Vui lòng thử lại.";
}

export function SearchErrorToast({ error, onDismiss }: SearchErrorToastProps) {
  useEffect(() => {
    // WHY: A transient failure should not leave a stale alert covering content indefinitely.
    const timeoutId = window.setTimeout(onDismiss, AUTO_DISMISS_MS);
    return () => window.clearTimeout(timeoutId);
  }, [error, onDismiss]);

  return (
    <div
      aria-atomic="true"
      className="fixed right-4 bottom-4 left-4 z-50 mx-auto flex max-w-md items-start gap-3 rounded-xl bg-neutral-950 p-4 text-sm text-white shadow-2xl sm:left-auto"
      role="alert"
    >
      <CircleAlert aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
      <div className="min-w-0 flex-1 space-y-1">
        <p className="font-medium">Tìm kiếm thất bại</p>
        <p className="leading-5 text-neutral-300">{getErrorMessage(error)}</p>
      </div>
      <Button
        aria-label="Đóng thông báo lỗi"
        className="-mt-1 -mr-1 text-neutral-300 hover:bg-white/10 hover:text-white"
        onClick={onDismiss}
        size="icon-sm"
        type="button"
        variant="ghost"
      >
        <X aria-hidden="true" />
      </Button>
    </div>
  );
}
