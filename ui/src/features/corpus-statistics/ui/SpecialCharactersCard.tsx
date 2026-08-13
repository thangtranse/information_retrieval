import type { SpecialCharacter } from "@/features/corpus-statistics/model/corpus-statistics";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";

interface SpecialCharactersCardProps {
  characters: SpecialCharacter[];
}

export function SpecialCharactersCard({ characters }: SpecialCharactersCardProps) {
  return (
    <Card className="bg-white">
      <CardHeader>
        <CardTitle className="text-xl">Ký tự đặc biệt</CardTitle>
        <CardDescription>
          Các ký tự ngoài chữ, số, khoảng trắng và tập dấu câu được cho phép.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {characters.length === 0 ? (
          <p className="rounded-lg border border-dashed px-4 py-8 text-center text-muted-foreground">
            Không phát hiện ký tự đặc biệt.
          </p>
        ) : (
          <div className="overflow-x-auto rounded-lg border">
            <table className="w-full min-w-xl text-sm">
              <caption className="sr-only">Danh sách ký tự đặc biệt trong segmented text</caption>
              <thead className="border-b bg-muted/40 text-left text-muted-foreground">
                <tr>
                  <th className="px-4 py-3 font-medium" scope="col">
                    Ký tự
                  </th>
                  <th className="px-4 py-3 font-medium" scope="col">
                    Code point
                  </th>
                  <th className="px-4 py-3 font-medium" scope="col">
                    Unicode name
                  </th>
                  <th className="px-4 py-3 text-right font-medium" scope="col">
                    Số lần
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {characters.map((item) => (
                  <tr key={item.code_point}>
                    <td className="px-4 py-3 text-lg font-semibold">{item.character}</td>
                    <td className="px-4 py-3 font-mono text-xs">{item.code_point}</td>
                    <td className="px-4 py-3 text-muted-foreground">{item.unicode_name}</td>
                    <td className="px-4 py-3 text-right font-medium tabular-nums">
                      {item.count.toLocaleString("vi-VN")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
