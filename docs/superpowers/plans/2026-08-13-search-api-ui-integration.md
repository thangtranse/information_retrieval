# Search API UI Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect the root search page to the existing semantic article search API with locked pending controls, visible processing feedback, ranked results, and toast errors.

**Architecture:** Keep the backend contract and request mutation inside `src/features/search`, extending the shared HTTP boundary only with a typed status error. `SearchPage` coordinates a TanStack Query mutation and focused UI components; it never recalculates or reorders backend results.

**Tech Stack:** React 19, TypeScript 6, TanStack Query 5, React Router 8, Tailwind CSS 4, Lucide React, Vite 8.

## Global Constraints

- Do not add dependencies or automated tests.
- Keep feature-specific code under `ui/src/features/search` and genuinely shared transport code under `ui/src/shared/api`.
- Disable only the textarea, search submit button, and Ctrl/Cmd + Enter while pending; navigation remains enabled.
- Hide all previous results immediately when a new request starts.
- Send strict `top_k: 10` for v1 and preserve backend result order.
- Every function containing business logic needs a WHY comment.
- Run root `make format` before committing and use scoped UI checks because the repository has a known unrelated backend notebook Ruff baseline failure.

---

### Task 1: Typed search transport and mutation

**Files:**
- Create: `ui/src/features/search/model/search.ts`
- Create: `ui/src/features/search/api/search-articles.ts`
- Create: `ui/src/features/search/model/use-article-search.ts`
- Modify: `ui/src/shared/api/endpoints.ts`
- Modify: `ui/src/shared/api/http-client.ts`

**Interfaces:**
- Produces: `SearchArticlesRequest`, `SearchArticlesResponse`, `RelatedArticle`, and `MatchedArticleSentence` wire types.
- Produces: `searchArticles(request: SearchArticlesRequest): Promise<SearchArticlesResponse>`.
- Produces: `useArticleSearch()` returning TanStack Query's mutation object.
- Produces: `ApiRequestError` with public `status: number`, still extending `Error` for existing callers.

- [ ] **Step 1: Define the exact backend wire model and v1 limit**

Create immutable TypeScript interfaces matching the FastAPI schema and export `SEARCH_TOP_K = 10`.

- [ ] **Step 2: Add the endpoint and typed transport failure**

Add `searchArticles: "/api/v1/search/articles"` to `API_ENDPOINTS`. Change non-2xx handling in `requestJson` to throw `ApiRequestError(response.status)`; do not expose response bodies or alter successful JSON parsing.

- [ ] **Step 3: Add the API adapter and mutation hook**

Post JSON with `Content-Type: application/json` through `requestJson`. Configure `useArticleSearch` with `mutationFn: searchArticles`; mutations should not retry by default.

- [ ] **Step 4: Verify the transport slice**

Run from `ui/`:

```bash
npm run format:check
npm run typecheck
npm run lint
```

Expected: all commands exit 0.

### Task 2: Processing, result, and toast components

**Files:**
- Create: `ui/src/features/search/ui/SearchProcessingState.tsx`
- Create: `ui/src/features/search/ui/SearchResults.tsx`
- Create: `ui/src/features/search/ui/SearchErrorToast.tsx`

**Interfaces:**
- Consumes: `SearchArticlesResponse` and `ApiRequestError` from Task 1.
- Produces: `SearchProcessingState()` with a polite live region.
- Produces: `SearchResults({ result }: { result: SearchArticlesResponse })` preserving array order.
- Produces: `SearchErrorToast({ error, onDismiss })` with status-specific Vietnamese copy and automatic dismissal.

- [ ] **Step 1: Render the pending state**

Add a card containing `LoaderCircle`, `aria-live="polite"`, and the copy `Đang phân đoạn và tìm bài viết liên quan…`.

- [ ] **Step 2: Render success and empty results**

Show query segment count and returned count. For every article, show rank, title fallback, external URL, formatted cosine similarity, matched query sentence, and matched article sentence. If `returned_count === 0`, show an explicit no-results card instead.

- [ ] **Step 3: Render and dismiss safe error toasts**

Map status 422 to invalid-content guidance, 503 to temporary-unavailability guidance, and every other failure to a generic retry message. Render a fixed responsive toast with `role="alert"`, a close button, and a 6-second dismissal timer that is cleaned up on unmount.

- [ ] **Step 4: Verify the UI component slice**

Run from `ui/`:

```bash
npm run format:check
npm run typecheck
npm run lint
```

Expected: all commands exit 0.

### Task 3: Wire the search page and lock pending interactions

**Files:**
- Modify: `ui/src/features/search/model/use-search-form.ts`
- Modify: `ui/src/features/search/ui/SearchForm.tsx`
- Modify: `ui/src/features/search/ui/SearchPage.tsx`

**Interfaces:**
- Consumes: `useArticleSearch`, `SEARCH_TOP_K`, `SearchProcessingState`, `SearchResults`, and `SearchErrorToast`.
- Changes: `SearchForm` accepts `isProcessing: boolean` and disables both its textarea and button while true.
- Changes: `useSearchForm().submit()` returns the trimmed query or `null` rather than storing a fake submitted result.

- [ ] **Step 1: Make form submission return normalized input**

Remove `submittedQuery`. Keep `query`, `canSubmit`, and `updateQuery`, and return the trimmed text from `submit()` so `SearchPage` owns the request boundary.

- [ ] **Step 2: Lock and label the form while pending**

Pass `disabled={isProcessing}` to the textarea, disable the button when processing or invalid, set `aria-busy`, and replace the search icon/copy with an animated loader and `Đang xử lý…`.

- [ ] **Step 3: Coordinate mutation states on the page**

Submit `{ text, top_k: SEARCH_TOP_K }`, guard Ctrl/Cmd + Enter while pending, render only the processing state during pending, only fresh results during success, and the error toast during failure. Calling `mutate` must transition away from old success data so previous results disappear immediately.

- [ ] **Step 4: Verify the integrated UI**

Run from `ui/`:

```bash
npm run format:check
npm run typecheck
npm run lint
npm run build
```

Expected: all commands exit 0 and Vite produces `dist/`.

### Task 4: Format, manually smoke, and commit

**Files:**
- Verify all files changed in Tasks 1-3 and both design documents.

**Interfaces:**
- Consumes: the completed feature.
- Produces: a clean implementation branch with reproducible static and manual evidence.

- [ ] **Step 1: Apply repository formatting**

Run from the repository root:

```bash
make format
```

Restore only the known unrelated backend notebook if Ruff rewrites it, then confirm the intended diff with `git status --short` and `git diff --check`.

- [ ] **Step 2: Run final scoped verification**

Run from `ui/`:

```bash
npm run format:check
npm run typecheck
npm run lint
npm run build
```

Expected: all commands exit 0.

- [ ] **Step 3: Run manual browser smoke checks**

Start the UI against the backend and verify: successful top-10 rendering, pending spinner, disabled textarea/button/shortcut, navigation remaining usable, old results disappearing on the next request, empty success state, 422 toast, 503/generic toast, toast close, and automatic dismissal. Inspect the browser console for errors and confirm result ordering matches the response payload.

- [ ] **Step 4: Commit the isolated feature**

Stage only the intended docs and UI files, then commit:

```bash
git commit -m "feat: integrate semantic search UI"
```
