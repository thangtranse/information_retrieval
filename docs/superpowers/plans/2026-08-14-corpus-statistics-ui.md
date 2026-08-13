# Corpus Statistics UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a responsive `/corpus/statistics` dashboard for the existing corpus statistics API.

**Architecture:** Keep request code, TypeScript contracts/query state, and presentation inside a dedicated `corpus-statistics` feature. Register only the shared endpoint and app route outside that feature, and reuse existing shadcn primitives and visual conventions.

**Tech Stack:** React 19, React Router 8, TanStack Query 5, TypeScript 6, Tailwind CSS 4, shadcn-style local components.

## Global Constraints

- Keep website code in `ui/` and feature-specific code under `src/features/corpus-statistics`.
- Do not create automated tests.
- Add WHY comments/docblocks to functions containing business logic.
- Do not add chart dependencies or refactor unrelated features.
- Use repository-local Prettier through `npm run format`.

---

### Task 1: API Contract and Query State

**Files:**
- Create: `ui/src/features/corpus-statistics/model/corpus-statistics.ts`
- Create: `ui/src/features/corpus-statistics/api/get-corpus-statistics.ts`
- Create: `ui/src/features/corpus-statistics/model/use-corpus-statistics.ts`
- Modify: `ui/src/shared/api/endpoints.ts`

**Interfaces:**
- Produce `CorpusStatistics`, distribution, Top word, and special-character response types matching the backend wire contract.
- Produce `getCorpusStatistics(topWordsLimit, signal)` and `useCorpusStatistics(topWordsLimit)`; query keys include the selected limit.

- [ ] Add the exact response types and query-key factory.
- [ ] Add the shared endpoint builder with `top_words_limit`.
- [ ] Implement the typed request adapter using `requestJson`.
- [ ] Implement the TanStack Query hook with abort-signal forwarding.
- [ ] Run `npm run format` and `npm run typecheck`.

### Task 2: Reusable Dashboard Presentation

**Files:**
- Create: `ui/src/features/corpus-statistics/ui/DistributionPanel.tsx`
- Create: `ui/src/features/corpus-statistics/ui/TopWordsCard.tsx`
- Create: `ui/src/features/corpus-statistics/ui/SpecialCharactersCard.tsx`

**Interfaces:**
- Consume typed model objects only; no component performs network requests.
- Distribution panels share the same metric order and Vietnamese number formatting.
- Top words accepts the selected union type and an `onLimitChange` callback.

- [ ] Build the normalized/segmented distribution panel using semantic tables inside shadcn cards.
- [ ] Build the ranked Top words card and native select styled to match existing shadcn controls.
- [ ] Build the responsive special-character table with semantic column headers.
- [ ] Run `npm run format`, `npm run lint`, and `npm run typecheck`.

### Task 3: Page States and Route

**Files:**
- Create: `ui/src/features/corpus-statistics/ui/CorpusStatisticsPage.tsx`
- Modify: `ui/src/app/router.tsx`

**Interfaces:**
- Route: `/corpus/statistics?top_words_limit=10|20|50|100`, defaulting invalid/missing values to `20`.
- Initial loading, populated, empty, and error/retry states follow the approved design.

- [ ] Parse and normalize the URL-backed limit, replacing invalid values only when the user changes the control.
- [ ] Compose header, refresh behavior, summary, two-column distributions, Top words, and special characters.
- [ ] Register the new route without changing existing routes.
- [ ] Run `npm run format`, `npm run lint`, `npm run typecheck`, and `npm run build`.

### Task 4: Manual Verification

**Files:**
- No source files added solely for verification.

- [ ] Run final UI format check, ESLint, TypeScript, and production build.
- [ ] Start backend and UI locally and smoke `/corpus/statistics` in a real browser.
- [ ] Verify loading/populated/empty/error states as available, responsive two-column/stacked layout, refresh, and URL-backed 10/20/50/100 limits.
- [ ] Run `git diff --check` and confirm unrelated/backend changes remain intact.
