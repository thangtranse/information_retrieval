import { useEffect, useState } from "react";
import { CircleCheck, LoaderCircle, TriangleAlert } from "lucide-react";

import { getHealth } from "@/features/health/api/get-health";
import type { Health } from "@/features/health/model/health";
import { Card, CardContent } from "@/shared/ui/card";

type HealthState =
  { kind: "loading" } | { kind: "ready"; health: Health } | { kind: "error"; message: string };

export function HealthStatus() {
  const [state, setState] = useState<HealthState>({ kind: "loading" });

  useEffect(() => {
    // WHY: Cancellation avoids committing a stale network result after the component unmounts.
    let active = true;

    void getHealth()
      .then((health) => {
        if (active) setState({ kind: "ready", health });
      })
      .catch((error: unknown) => {
        if (active) {
          const message = error instanceof Error ? error.message : "Unknown API error";
          setState({ kind: "error", message });
        }
      });

    return () => {
      active = false;
    };
  }, []);

  if (state.kind === "loading") {
    return (
      <Card aria-live="polite" className="border-0 shadow-sm ring-1 ring-black/5">
        <CardContent className="flex items-center gap-3 py-2 text-muted-foreground">
          <LoaderCircle aria-hidden="true" className="size-5 animate-spin" />
          <p>Đang kiểm tra kết nối backend…</p>
        </CardContent>
      </Card>
    );
  }

  if (state.kind === "error") {
    return (
      <Card className="border-destructive/20 bg-destructive/5 shadow-sm ring-destructive/20">
        <CardContent className="flex items-start gap-3 py-2">
          <TriangleAlert aria-hidden="true" className="mt-0.5 size-5 text-destructive" />
          <div className="space-y-1">
            <p className="font-medium">Không thể kết nối backend</p>
            <p className="text-sm text-muted-foreground" role="alert">
              {state.message}
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-0 shadow-sm ring-1 ring-black/5">
      <CardContent className="py-2">
        <div className="mb-5 flex items-center gap-2 text-sm font-medium text-emerald-700">
          <CircleCheck aria-hidden="true" className="size-5" />
          Backend đang hoạt động
        </div>
        <dl className="grid gap-4">
          <div className="flex items-center justify-between gap-4 border-b pb-4">
            <dt className="text-muted-foreground">Trạng thái</dt>
            <dd className="font-medium">{state.health.status}</dd>
          </div>
          <div className="flex items-center justify-between gap-4 border-b pb-4">
            <dt className="text-muted-foreground">Dịch vụ</dt>
            <dd className="font-medium">{state.health.service}</dd>
          </div>
          <div className="flex items-center justify-between gap-4">
            <dt className="text-muted-foreground">Môi trường</dt>
            <dd className="font-medium">{state.health.environment}</dd>
          </div>
        </dl>
      </CardContent>
    </Card>
  );
}
