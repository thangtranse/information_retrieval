import { QueryClientProvider } from "@tanstack/react-query";
import { Outlet } from "react-router";

import { queryClient } from "@/app/query-client";
import { ScrollToTopButton } from "@/shared/ui/scroll-to-top-button";

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Outlet />
      <ScrollToTopButton />
    </QueryClientProvider>
  );
}
