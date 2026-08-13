# Home Corpus Link and Scroll-to-Top Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Link the home page to Corpus Statistics and add an accessible global scroll-to-top button.

**Architecture:** Keep the home navigation addition inside the search feature. Implement scroll visibility and motion policy in one shared UI component mounted once by the app shell.

**Tech Stack:** React 19, TypeScript 6, React Router 8, Tailwind CSS 4, local shadcn-style Button.

## Global Constraints

- Keep website code in `ui/`; only reusable UI belongs in `src/shared`.
- Do not create automated tests or add dependencies.
- Add WHY comments to business or interaction-policy functions.
- Use repository-local Prettier through `npm run format`.

---

### Task 1: Home Navigation Entry

**Files:**
- Modify: `ui/src/features/search/ui/SearchPage.tsx`

**Interfaces:**
- Produce a “Thống kê corpus” link to `/corpus/statistics` using `BarChart3` and the existing secondary-navigation style.

- [ ] Add the icon import and navigation link without changing existing entries.
- [ ] Run `npm run format` and `npm run typecheck`.

### Task 2: Global Scroll-to-Top Control

**Files:**
- Create: `ui/src/shared/ui/scroll-to-top-button.tsx`
- Modify: `ui/src/app/App.tsx`

**Interfaces:**
- Produce `ScrollToTopButton()` with a 400-pixel visibility threshold and reduced-motion-aware behavior.
- Mount one instance alongside `Outlet` so all routes receive the control.

- [ ] Subscribe to the passive window scroll event and clean it up on unmount.
- [ ] Render nothing below the threshold; otherwise render a fixed shadcn icon Button.
- [ ] Scroll to `top: 0` using `smooth` or `auto` based on `prefers-reduced-motion`.
- [ ] Mount the component in the app shell.
- [ ] Run `npm run format`, `npm run lint`, `npm run typecheck`, and `npm run build`.

### Task 3: Manual Verification

**Files:**
- No source files added solely for verification.

- [ ] Browser-smoke the home link and verify it opens `/corpus/statistics`.
- [ ] Verify the button is absent at the top, appears after more than 400 pixels, and returns to the top when clicked.
- [ ] Verify the same behavior on the Corpus Statistics route and a mobile viewport.
- [ ] Run fresh format check, lint, typecheck, build, and `git diff --check`.
