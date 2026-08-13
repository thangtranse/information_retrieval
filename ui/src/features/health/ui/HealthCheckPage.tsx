import { ArrowLeft, Activity } from "lucide-react";
import { Link } from "react-router";

import { HealthStatus } from "@/features/health/ui/HealthStatus";
import { Button } from "@/shared/ui/button";

export function HealthCheckPage() {
  return (
    <main className="min-h-svh bg-linear-to-b from-neutral-50 to-white px-4 py-8 sm:py-14">
      <div className="mx-auto flex w-full max-w-2xl flex-col gap-8">
        <Button asChild className="w-fit" variant="ghost">
          <Link to="/">
            <ArrowLeft aria-hidden="true" />
            Quay lại tìm kiếm
          </Link>
        </Button>

        <header className="space-y-4">
          <div className="flex size-11 items-center justify-center rounded-xl bg-neutral-950 text-white shadow-sm">
            <Activity aria-hidden="true" className="size-5" />
          </div>
          <div className="space-y-2">
            <p className="text-sm font-medium tracking-wide text-muted-foreground uppercase">
              Information Retrieval
            </p>
            <h1 className="font-heading text-3xl font-semibold tracking-tight sm:text-4xl">
              Kiểm tra hệ thống
            </h1>
            <p className="max-w-xl text-muted-foreground">
              Theo dõi kết nối giữa giao diện và dịch vụ backend hiện tại.
            </p>
          </div>
        </header>

        <HealthStatus />
      </div>
    </main>
  );
}
