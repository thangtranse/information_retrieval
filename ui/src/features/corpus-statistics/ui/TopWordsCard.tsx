import {
  TOP_WORD_LIMITS,
  type TopWord,
  type TopWordsLimit,
} from "@/features/corpus-statistics/model/corpus-statistics";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";

interface TopWordsCardProps {
  isFetching: boolean;
  onLimitChange: (limit: TopWordsLimit) => void;
  selectedLimit: TopWordsLimit;
  words: TopWord[];
}

export function TopWordsCard({
  isFetching,
  onLimitChange,
  selectedLimit,
  words,
}: TopWordsCardProps) {
  return (
    <Card className="bg-white">
      <CardHeader className="gap-4 sm:grid-cols-[1fr_auto]">
        <div className="space-y-1">
          <CardTitle className="text-xl">Top words</CardTitle>
          <CardDescription>
            Các token chứa dấu gạch dưới, xếp theo số lần xuất hiện.
          </CardDescription>
        </div>
        <label className="flex items-center gap-2 text-sm font-medium">
          Hiển thị
          <select
            aria-label="Số lượng Top words"
            className="h-8 rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none transition-colors focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:opacity-50"
            disabled={isFetching}
            onChange={(event) => onLimitChange(Number(event.target.value) as TopWordsLimit)}
            value={selectedLimit}
          >
            {TOP_WORD_LIMITS.map((limit) => (
              <option key={limit} value={limit}>
                {limit}
              </option>
            ))}
          </select>
        </label>
      </CardHeader>
      <CardContent>
        {words.length === 0 ? (
          <p className="rounded-lg border border-dashed px-4 py-8 text-center text-muted-foreground">
            Chưa có token chứa dấu gạch dưới.
          </p>
        ) : (
          <ol className="divide-y rounded-lg border">
            {words.map((item, index) => (
              <li className="flex items-center gap-3 px-4 py-3" key={item.word}>
                <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-neutral-950 text-xs font-semibold text-white">
                  {index + 1}
                </span>
                <code className="min-w-0 flex-1 truncate text-sm font-medium">{item.word}</code>
                <span className="tabular-nums text-muted-foreground">
                  {item.count.toLocaleString("vi-VN")}
                </span>
              </li>
            ))}
          </ol>
        )}
      </CardContent>
    </Card>
  );
}
