import { QueryClientProvider } from "@tanstack/react-query";
import { Outlet } from "react-router";

import { queryClient } from "@/app/query-client";

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Outlet />
    </QueryClientProvider>
  );
}
