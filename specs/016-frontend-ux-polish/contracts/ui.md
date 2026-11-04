# UI Contracts: 016-frontend-ux-polish

**Feature**: 016-frontend-ux-polish | **Date**: 2026-11-04

No REST/API contracts (no backend change). These are the UI-level contracts tests assert.

## C1 — Tab-scoped search (FR-001/FR-002)

- Journey tab: no `role="search"` element present, whatever the query state.
- Routes tab: exactly one search box; typing debounces and paginates (`Pager` kind="routes").
- Stops tab: exactly one search box; typing debounces and paginates (`Pager` kind="stops").
- Sticky: `.gonaj-search` inside tab panels keeps `position: sticky` behavior.

## C2 — Mobile overlay cap + close restore (FR-003)

- At ≤48rem width: `.gonaj-overlay` computed `max-height` ≤ 50% viewport; content scrolls internally (`overflow-y: auto`); map container remains visible/interactive.
- No collapse/expand control exists in the overlay.
- Close → previously active tab (Journey/Routes/Stops) with its search results intact.

## C3 — Route focus vs stop centering (FR-004/FR-009)

- Route open: map shows only the route polyline + route stops; generic `area.markers` hidden; bounds fitted; origin/destination markers visually distinct with accessible names differing from intermediate stops.
- Stop card open: map centers on the stop; area markers remain.
- Overlay closed: area markers restored.

## C4 — Dictate hint + recording (FR-005)

- Persistent visible text `Press and hold to record` + tooltip on the Dictate button.
- Quick tap (<~300ms): inline explanation appears; no `getUserMedia`/`MediaRecorder`/`postTranscribe` call.
- Hold: pulsing red dot (static under `prefers-reduced-motion`) + `Listening… release to send` with `role="status"`; Ask disabled until release.

## C5 — Mutual clear (FR-006)

- Ask submit or transcribe-complete → direct inputs (`From stop`, `To stop`), candidate menus, and direct results cleared.
- Direct typing/selecting/Find → question text, answer cards, pager, filter, candidate map highlights cleared.
- Mid-selection abandonment either way leaves no stale state.

## C6 — Ask lock + Stop (FR-007)

- While ask `status==loading`: From/To inputs, candidate selection, and `Find direct routes` disabled; `Stop` button visible.
- `Stop` → ask aborts, panel idle, question text preserved, no direct search fired.

## C8 — Marker name labels (FR-010)

- With ≤12 rendered stops inside the map bounds: every marker shows a full-size permanent name label (themed `.gonaj-marker-label`), area and route-focus alike.
- With 13–24 in view: the same names render compact (`.gonaj-marker-label.is-compact`).
- With more stops in view (or zero): no permanent labels; endpoint pins still expose name + role via `title`/`alt`.
- Panning/zooming across the thresholds toggles labels with no refetch.

## C7 — Footer version (FR-008)

- Selector: `footer.gonaj-version`, `data-testid="app-version"`, small muted text.
- With metadata: `v{version}+{sha7} · built {UTC}`.
- Without SHA (or all metadata): `v{version}` (plus `· built {UTC}` when time known); UI renders regardless.
