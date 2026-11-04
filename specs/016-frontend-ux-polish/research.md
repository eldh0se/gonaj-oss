# Research: 016-frontend-ux-polish

**Feature**: 016-frontend-ux-polish | **Date**: 2026-11-04

All Technical Context unknowns were resolved by the user brief + clarify + repo inspection. No NEEDS CLARIFICATION remains.

## Decision: Scoped search placement (FR-001/FR-002)

- Decision: Remove the single `<SearchBox onQuery>` from `MapPage`'s aside; render one `SearchBox` each inside the Routes and Stops tab panels in `ResultsList.jsx`, hoisted so Journey tab never receives one. Keep the single shared `query` state + debounce (300ms in `SearchBox.jsx`) + `Pager` + loading/no-match/error states untouched.
- Rationale: One state, two inputs — search/pager/error behavior and sticky header context (`.gonaj-results .gonaj-search`) keep working with no logic change.
- Alternatives considered: Per-tab query states — rejected, doubles fetches and breaks the shared pager/reset semantics in `App.jsx`.

## Decision: Mobile cap value + close behavior (FR-003)

- Decision: Change the `max-width:48rem` `.gonaj-overlay` rule from `max-height:70dvh` to `50dvh`, keep internal `overflow-y:auto`, keep map interactive underneath. No collapse/expand control; close restores the previously visible tab content (spec edge case, already true — tab state lives in `ResultsList`, untouched by overlay open/close).
- Rationale: 50dvh is the spec ceiling; closing restores tabs for free since overlay open/close never touches tab/search state.
- Alternatives considered: New bottom-sheet component — explicitly rejected during clarify (reuse existing overlay).

## Decision: Permanent stop-name labels gated by visible count (FR-010)

- Decision: `MapView` binds permanent name tooltips (`bindTooltip(name, {permanent: true})` with a themed `.gonaj-marker-label` class) on every rendered marker — area and route-focus alike — in two tiers: full-size at ≤12 in bounds (`FULL_LABEL_MAX`), compact (same names, smaller, `.is-compact`) at 13–24 (`MAX_LABELLED_VISIBLE`, tuned up from 6 after phone field feedback showed 6 too shy at real density, then split when 24 full-size cluttered the converging level). Above 24, labels unbind. Count recomputes on marker changes and on `moveend` (pan/zoom), with no refetch. Endpoint pins keep their `title`/`alt` regardless.
- Rationale: Count-gating (not a fixed zoom) implements the request literally — labels appear once the view holds a readable handful, before extreme zoom — and self-limits clutter in dense areas while working uniformly for sparse ones.
- Alternatives considered: Fixed zoom threshold (e.g. 15+) — rejected, density varies so one zoom is crowded in one place and barren in another; hover-only tooltips — rejected by the requester in favor of permanent labels.

## Decision: Route focus vs stop centering (FR-004/FR-009)

- Decision: Route open → `MapView` receives only the route polyline + route-stop markers, `area.markers` hidden, `fitBounds` to route bounds, origin/destination rendered distinctly (color/shape + accessible labels, not plain `circleMarker`). Stop card → `setCenter` on the stop, `area.markers` stay. Close → restore area markers.
- Rationale: All props (`markers`, `highlight`, `fitBounds`, `center`, `selectedId`) already exist on `MapView`; the work is prop wiring in `App.jsx` plus distinct marker rendering — no Leaflet API change. `fitBounds`/`setView` effects already implemented.
- Alternatives considered: New map layer for focus — rejected, `markerLayerRef`/`highlightLayerRef` split already supports it.

## Decision: Press-and-hold detection (FR-005)

- Decision: Keep `onPointerDown/Up/Leave` on the Dictate button; add persistent hint text + `title`, a `Date.now()` delta for the <~300ms short-tap inline explanation (never starts capture/transcribe), and a recording state (`recording==true` → pulsing red dot + `Listening… release to send` with `role=status`/`aria-live`, Ask disabled). Static red dot under `prefers-reduced-motion` (CSS media query).
- Rationale: Matches existing recorder flow (`startDictation`/`stopDictation`); tap-vs-hold is a timestamp comparison, no new timing infra.
- Alternatives considered: Separate tap/hold buttons — rejected, breaks the single-press-hold affordance the brief pins.

## Decision: Mutual clear + ask lock (FR-006/FR-007)

- Decision: Wire the existing clear paths both ways: ask submit / transcribe-complete resets `fromText/fromStop/toText/toStop`, candidate menus, `direct`; direct input/select/Find resets `question`, ask `state/cards/paging/filter`, candidate map highlights (via `onShowCandidates(null)`). During `state.status==loading`, disable From/To inputs, candidate selection, Find; `Stop` button aborts `askAbort`, restores idle, preserves question text; guard `findDirectRoutes` against concurrent ask.
- Rationale: Both `ask()` and `findDirectRoutes()` already abort the other path's controller (`askAbort`/`directAbort`); the gap is state reset + disabled UI + abort button, all local to `JourneyPanel.jsx`.
- Alternatives considered: Shared query-mode reducer — rejected, overkill; two directional resets cover it.

## Decision: Version source (FR-008)

- Decision: Vite `define` injects `__APP_VERSION__` (from `package.json:0.1.0`), `__APP_SHA__` (git rev-parse short, empty when unavailable), `__APP_BUILT_AT__` (UTC build time) via `vite.config.js`; footer reads them with fallback to `v{version}` (`v0.1.0` default). Render in `footer.gonaj-version` (`data-testid="app-version"`), small muted text.
- Rationale: Zero runtime API, works in every deploy, graceful when metadata is missing — exactly what FR-008/AC2 require.
- Alternatives considered: Backend `/meta` endpoint — rejected, spec pins no-backend-change; version is a build fact, not server state.
