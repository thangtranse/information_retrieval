import { Navigate, createBrowserRouter } from "react-router";

import { App } from "@/app/App";
import { ArticleImportPage } from "@/features/article-import/ui/ArticleImportPage";
import { CrawledArticlePage } from "@/features/article-list/ui/CrawledArticlePage";
import { CorpusStatisticsPage } from "@/features/corpus-statistics/ui/CorpusStatisticsPage";
import { HealthCheckPage } from "@/features/health/ui/HealthCheckPage";
import { SearchPage } from "@/features/search/ui/SearchPage";

export const router = createBrowserRouter([
  {
    Component: App,
    children: [
      { index: true, Component: SearchPage },
      { path: "articles/import", Component: ArticleImportPage },
      { path: "articles/crawled", Component: CrawledArticlePage },
      { path: "corpus/statistics", Component: CorpusStatisticsPage },
      { path: "health-check", Component: HealthCheckPage },
      { path: "*", element: <Navigate replace to="/" /> },
    ],
  },
]);
