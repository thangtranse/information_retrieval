import { ArrowLeft, BarChart3, Database, RefreshCcw } from "lucide-react";
import { Link, useSearchParams } from "react-router";

import {
  parseTopWordsLimit,
  type TopWordsLimit,
} from "@/features/corpus-statistics/model/corpus-statistics";
import { useCorpusStatistics } from "@/features/corpus-statistics/model/use-corpus-statistics";
import { DistributionPanel } from "@/features/corpus-statistics/ui/DistributionPanel";
import { SpecialCharactersCard } from "@/features/corpus-statistics/ui/SpecialCharactersCard";
import { TopWordsCard } from "@/features/corpus-statistics/ui/TopWordsCard";
import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardHeader } from "@/shared/ui/card";
import { Skeleton } from "@/shared/ui/skeleton";

function DashboardSkeleton() {
  return (
    <div aria-label="Đang tải thống kê corpus" className="space-y-6">
      <Card className="bg-white">
        <CardContent className="space-y-3 py-2">
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-10 w-28" />
        </CardContent>
      </Card>
      <div className="grid gap-6 lg:grid-cols-2">
        {[0, 1].map((item) => (
          <Card className="bg-white" key={item}>
            <CardHeader className="space-y-2">
              <Skeleton className="h-6 w-52" />
              <Skeleton className="h-4 w-4/5" />
            </CardHeader>
            <CardContent className="grid gap-4 xl:grid-cols-2">
              <Skeleton className="h-80 w-full" />
              <Skeleton className="h-80 w-full" />
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

export function CorpusStatisticsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const topWordsLimit = parseTopWordsLimit(searchParams.get("top_words_limit"));
  const statisticsQuery = useCorpusStatistics(topWordsLimit);

  const updateTopWordsLimit = (limit: TopWordsLimit) => {
    /** WHY: Replacing the query keeps analysis controls shareable without polluting browser history. */
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set("top_words_limit", String(limit));
    setSearchParams(nextParams, { replace: true });
  };

  const refresh = () => {
    /** WHY: Explicit refresh lets corpus operators request fresh aggregates after a pipeline run. */
    void statisticsQuery.refetch();
  };

  const statistics = statisticsQuery.data;

  return (
    <main className="min-h-svh bg-linear-to-b from-neutral-50 via-white to-neutral-100 px-4 py-8 sm:py-14">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-8">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Button asChild className="w-fit" variant="ghost">
            <Link to="/">
              <ArrowLeft aria-hidden="true" />
              Quay lại tìm kiếm
            </Link>
          </Button>
          <Button
            disabled={statisticsQuery.isFetching}
            onClick={refresh}
            type="button"
            variant="outline"
          >
            <RefreshCcw
              aria-hidden="true"
              className={statisticsQuery.isFetching ? "animate-spin" : undefined}
            />
            Làm mới
          </Button>
        </div>

        <header className="space-y-4">
          <div className="space-y-2">
            <p className="text-sm font-medium tracking-[0.16em] text-muted-foreground uppercase">
              Phân tích dữ liệu
            </p>
            <h1 className="font-heading text-4xl font-semibold tracking-tight sm:text-5xl">
              Thống kê corpus
            </h1>
            <p className="max-w-3xl text-base leading-7 text-muted-foreground sm:text-lg">
              Đối chiếu phân phối văn bản chuẩn hóa và văn bản đã tách từ, cùng các token và ký tự
              đáng chú ý trong toàn bộ corpus.
            </p>
          </div>
        </header>

        {statisticsQuery.isPending ? <DashboardSkeleton /> : null}

        {statisticsQuery.isError ? (
          <Card className="bg-white text-center">
            <CardContent className="space-y-4 py-10">
              <p role="alert">Không thể tải thống kê corpus.</p>
              <Button onClick={refresh} type="button" variant="outline">
                <RefreshCcw aria-hidden="true" />
                Thử lại
              </Button>
            </CardContent>
          </Card>
        ) : null}

        {statistics && statistics.document_count === 0 ? (
          <Card className="bg-white text-center">
            <CardContent className="space-y-3 py-12">
              <Database aria-hidden="true" className="mx-auto size-8 text-muted-foreground" />
              <p className="text-lg font-medium">Corpus chưa có dữ liệu thống kê</p>
              <p className="text-muted-foreground">
                Hãy chạy pipeline segment để tạo snapshot corpus cho các bài viết.
              </p>
            </CardContent>
          </Card>
        ) : null}

        {statistics && statistics.document_count > 0 ? (
          <div className="space-y-6">
            <section aria-label="So sánh phân phối corpus" className="grid gap-6 lg:grid-cols-2">
              <DistributionPanel
                description="Thống kê từ normalized_text trước khi áp dụng word segmentation."
                distributions={statistics.normalized}
                title="Văn bản chuẩn hóa"
              />
              <DistributionPanel
                description="Thống kê từ segmented_text sau khi xử lý bằng VnCoreNLP."
                distributions={statistics.segmented}
                title="Văn bản đã tách từ"
              />
            </section>

            <section className="grid items-start gap-6 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
              <TopWordsCard
                isFetching={statisticsQuery.isFetching}
                onLimitChange={updateTopWordsLimit}
                selectedLimit={topWordsLimit}
                words={statistics.top_words}
              />
              <SpecialCharactersCard characters={statistics.special_characters} />
            </section>
          </div>
        ) : null}
      </div>
    </main>
  );
}
