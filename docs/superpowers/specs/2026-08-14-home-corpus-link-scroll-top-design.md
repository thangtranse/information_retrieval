# Home Corpus Link and Scroll-to-Top Design

## Goal

Expose the Corpus Statistics page from the home navigation and provide a reusable scroll-to-top
control on every application route.

## Design

Add a fourth secondary-navigation link on the home search page. The link uses the existing inline
navigation style, a `BarChart3` icon, the Vietnamese label “Thống kê corpus”, and points to
`/corpus/statistics`.

Create `ScrollToTopButton` as a shared UI component and mount it once in `App`, alongside the route
outlet. It listens to the window scroll position and becomes visible only after the document has
scrolled more than 400 pixels. The control is fixed above the bottom-right safe area, uses the
existing shadcn `Button` icon style, and has an accessible Vietnamese label and title.

Clicking scrolls the window to the top. Use smooth scrolling unless the user requests reduced
motion, in which case use immediate scrolling. Visibility transitions must not leave an invisible
focusable control: render no button while it is hidden.

## Scope and Verification

Keep home-specific navigation changes inside `SearchPage`; keep the reusable control under
`src/shared/ui`. Do not add dependencies, tests, or unrelated layout refactors. Verify with
repository-local Prettier, ESLint, TypeScript, production build, and browser smoke covering the home
link, hidden/visible thresholds, click behavior, and at least one non-home route.
