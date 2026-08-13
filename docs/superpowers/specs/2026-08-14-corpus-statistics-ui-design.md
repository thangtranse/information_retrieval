# Corpus Statistics UI Design

## Goal

Add a dedicated `/corpus/statistics` page that presents the existing corpus statistics API in the
same monochrome, card-based visual language as the current application. The page must make the
normalized and segmented corpus distributions easy to compare without adding a chart dependency.

## Architecture

Keep all feature-specific code under `ui/src/features/corpus-statistics`, separated into `api`,
`model`, and `ui`. The API adapter calls `GET /api/v1/corpus/statistics`; a TanStack Query hook owns
server state and caches results by `top_words_limit`; presentation components receive typed data and
do not perform requests directly. Only the route registration and shared API endpoint registry live
outside the feature.

The route is `/corpus/statistics`. The selected Top words limit is stored in the URL as
`top_words_limit` and accepts `10`, `20`, `50`, or `100`. Missing or invalid values resolve to `20`
without sending an invalid backend request. Updating the control replaces the current URL query and
causes TanStack Query to load/cache that limit.

## Page Design

Use the established neutral gradient background, Geist headings, restrained shadows, rounded cards,
and current responsive spacing. The header contains a statistics icon, page title and short
description, a link back to search, and a refresh button.

The populated view contains:

1. A summary card showing `document_count`.
2. Two equal-width distribution panels on desktop and a vertical stack on mobile: “Văn bản chuẩn
   hóa” and “Văn bản đã tách từ”. Each panel contains Word count and Sentence count tables with rows
   ordered `Min`, `P25`, `Median`, `Mean`, `P75`, `P95`, `Max`. Matching layout and row order are an
   invariant so the two panels can be compared directly. Tables may scroll horizontally on narrow
   screens.
3. A Top words card with a shadcn-style 10/20/50/100 limit control and ranked rows containing the
   original token and occurrence count.
4. A special-character card containing character, code point, Unicode name, and occurrence count.
   It becomes horizontally scrollable instead of dropping columns on narrow screens.

Format finite metric values with the Vietnamese locale and at most two decimal places. Render API
`null` metrics as an em dash. Preserve Top word tokens and special characters exactly as returned.

## States and Accessibility

The initial loading state uses skeletons shaped like the final summary and content cards. A fetch
failure replaces the dashboard with an alert card and retry button. Manual refresh keeps the current
data visible while fetching and disables/animates the refresh control. A successful response with
`document_count === 0` shows one corpus-empty card and omits all metric, Top words, and special
character panels.

Controls have visible labels, loading and error content is announced semantically, decorative icons
are hidden from assistive technology, and tables use captions or accessible headings plus semantic
headers. Keyboard navigation follows native link/button/select behavior.

## Scope and Verification

Reuse existing shadcn components from `src/shared/ui`. Add a focused shared component only when a
required shadcn primitive is absent; do not add chart or visualization dependencies. Do not refactor
existing features beyond registering the new route and endpoint.

Per repository policy, do not add automated tests. Verify with repository-local Prettier, ESLint,
TypeScript type checking, production build, and manual browser smoke for loading, populated, empty,
error/retry, responsive two-column/stacked layout, refresh, and URL-backed Top words limits.
