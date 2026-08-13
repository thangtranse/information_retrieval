import type {
  CorpusDistributions,
  Distribution,
} from "@/features/corpus-statistics/model/corpus-statistics";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";

const METRICS = [
  ["min", "Min"],
  ["p25", "P25"],
  ["median", "Median"],
  ["mean", "Mean"],
  ["p75", "P75"],
  ["p95", "P95"],
  ["max", "Max"],
] as const;

const numberFormatter = new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 2 });

function formatMetric(value: number | null): string {
  /** WHY: A visible placeholder distinguishes an empty corpus from a measured zero. */
  return value === null ? "—" : numberFormatter.format(value);
}

interface MetricTableProps {
  label: string;
  distribution: Distribution;
}

function MetricTable({ distribution, label }: MetricTableProps) {
  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="w-full min-w-72 text-sm">
        <caption className="border-b bg-muted/40 px-4 py-3 text-left font-medium text-foreground">
          {label}
        </caption>
        <thead className="sr-only">
          <tr>
            <th scope="col">Chỉ số</th>
            <th scope="col">Giá trị</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {METRICS.map(([key, metricLabel]) => (
            <tr key={key}>
              <th className="px-4 py-2.5 text-left font-normal text-muted-foreground" scope="row">
                {metricLabel}
              </th>
              <td className="px-4 py-2.5 text-right font-medium tabular-nums">
                {formatMetric(distribution[key])}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface DistributionPanelProps {
  description: string;
  distributions: CorpusDistributions;
  title: string;
}

export function DistributionPanel({ description, distributions, title }: DistributionPanelProps) {
  return (
    <Card className="bg-white">
      <CardHeader>
        <CardTitle className="text-xl">{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
        <MetricTable distribution={distributions.word_count} label="Số từ mỗi bài" />
        <MetricTable distribution={distributions.sentence_count} label="Số câu mỗi bài" />
      </CardContent>
    </Card>
  );
}
