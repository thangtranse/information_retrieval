import { LoaderCircle } from "lucide-react";

import { Card, CardContent } from "@/shared/ui/card";

export function SearchProcessingState() {
  return (
    <Card
      aria-busy="true"
      aria-live="polite"
      className="border-0 bg-white/90 shadow-lg shadow-black/5"
    >
      <CardContent className="flex items-center justify-center gap-3 py-8 text-muted-foreground">
        <LoaderCircle aria-hidden="true" className="size-5 animate-spin" />
        <p>Đang phân đoạn và tìm bài viết liên quan…</p>
      </CardContent>
    </Card>
  );
}
