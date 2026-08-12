import { Navigate, createBrowserRouter } from "react-router";

import { App } from "@/app/App";
import { HealthCheckPage } from "@/features/health/ui/HealthCheckPage";
import { SearchPage } from "@/features/search/ui/SearchPage";

export const router = createBrowserRouter([
  {
    Component: App,
    children: [
      { index: true, Component: SearchPage },
      { path: "health-check", Component: HealthCheckPage },
      { path: "*", element: <Navigate replace to="/" /> },
    ],
  },
]);
