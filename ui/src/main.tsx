import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router";

import { router } from "@/app/router";

import "@/styles/global.css";

const root = document.getElementById("root");

if (!root) {
  throw new Error("Root element is required to mount the application");
}

createRoot(root).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
);
