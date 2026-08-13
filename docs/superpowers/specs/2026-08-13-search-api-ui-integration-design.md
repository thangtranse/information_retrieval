# Search API UI Integration Design

## Goal

Connect the existing search page to `POST /api/v1/search/articles` so a user can submit Vietnamese text, see processing feedback, and inspect ranked related articles without leaving the page.

## Approved interaction

- Submit trimmed text with a fixed v1 `top_k` of 10.
- While the request is pending, remove every previous result and show an explicit processing state.
- Disable the search textarea, submit button, and Ctrl/Cmd + Enter shortcut until the request settles.
- Keep secondary navigation links usable during processing.
- On failure, unlock the form, keep old results hidden, and show a dismissible Vietnamese toast that disappears automatically.
- On success, show the segmented-query count and the distinct ranked articles returned by the backend.
- Show a dedicated empty state when the API succeeds with no related articles.

## Architecture

The search feature follows the UI's existing feature boundaries. A typed API adapter owns the wire contract, a TanStack Query mutation owns server-state transitions, and focused presentational components render processing, results, and errors. `SearchPage` coordinates these pieces but does not implement transport details.

No dependency is added. A search-local error toast is sufficient for the current requirement and avoids introducing an application-wide notification abstraction before another feature needs it. The shared HTTP client will expose a typed status error so the search feature can translate 422, 503, and unexpected failures into appropriate Vietnamese messages without changing existing callers' success behavior.

## API contract

Request:

```json
{
  "text": "Nội dung cần tìm",
  "top_k": 10
}
```

The response model mirrors the backend fields exactly: `status`, `top_k`, `returned_count`, segmented query information, and article entries containing rank, title, URL, cosine score, matched query sentence, and matched article sentence metadata.

## Rendering

The pending state uses an animated loader with `aria-live` and `aria-busy`. Search results are ordered exactly as returned by the backend and display rank, title fallback, source link, cosine similarity, and both sides of the best matching sentence pair. The UI does not re-rank or recalculate cosine values.

The toast uses `role="alert"`, contains no raw backend or network diagnostics, and maps known HTTP statuses to user-facing copy. It is displayed only after a failed request, so its dismiss button does not conflict with the pending-state lock.

## Verification

The repository explicitly prohibits adding automated tests for this task. Verification therefore consists of repository-local Prettier, ESLint, TypeScript type checking, the Vite production build, and manual browser/API smoke checks for success, empty results, pending lock, keyboard lock, and error toast behavior.
