# Research: Route Map

**Feature**: [spec.md](spec.md) | **Date**: 2026-10-29

The spec fixes the page architecture (one page, overlay,
deep-linkable `/routes/:id`, inert chat dock) and the
constitution fixes the provider rules (Leaflet, OSM public
tiles with attribution, no Nominatim, no accounts/tracking).
No NEEDS CLARIFICATION remained. Each decision below records
what was chosen, why, and what was set aside. UI shapes are
normative in [contracts/ui-contracts.md](contracts/ui-contracts.md).

## Decision: Raw Leaflet behind a single MapView adapter (no react-leaflet)

- **Decision**: Render with the `leaflet` package driven
  imperatively from one `MapView.jsx` adapter module (map
  instance, tile layer, markers, viewport callback). No
  `react-leaflet` binding layer. All other components talk to
  the adapter's props/callbacks, never to Leaflet globals.
- **Rationale**: Fewest moving parts for one map; the
  provider-integration isolation the constitution demands is
  a single module boundary, so a Leaflet→MapLibre GL JS swap
  (`maplibre-gl`, BSD-3-Clause — explicitly not `mapbox-gl`, which is
  proprietary since v2 and billed per load) rewrites `MapView.jsx` only.
  (MapLibre is vector-first, so a future swap additionally needs a
  vector-tile-source decision.) Avoids binding-version churn
  between React, Leaflet, and a wrapper.
- **Alternatives considered**: `react-leaflet` (rejected —
  extra dependency and version coupling for declarative
  syntax the single map does not need); hand-rolled canvas
  map (rejected — rebuilding tiles, zoom, and attribution
  violates the OSM-only rule's spirit and wastes the
  mandate).

## Decision: react-router-dom for the `/routes/:id` address

- **Decision**: `react-router-dom` with two routes rendering
  the same page component: `/` (map-browse) and
  `/routes/:id` (map page with the detail overlay open for
  that id). Unknown paths render the map-browse view, never
  an error page.
- **Rationale**: Deep-linkable evidence URLs that a reviewer
  can copy, reload, and share (spec Story 3/AC3) need a real
  addressable route; a router is the standard mechanism, and
  it leaves room to split the overlay into a real second
  page later without changing addresses.
- **Alternatives considered**: Hand-rolled History-API
  switch (rejected — reimplements matching, params, and
  fallback for no gain); hash-only overlay state (rejected —
  evidence links must be shareable plain URLs, and the 004
  contract already fixes `/routes/:id`).

## Decision: JSX matching the scaffold, TypeScript deferred

- **Decision**: New files use JSX like the scaffolded
  `main.jsx`; no TypeScript conversion in this feature and no
  `tsconfig`/loader changes.
- **Rationale**: Consistency with the existing scaffold wins
  over a mid-stream language migration; the scaffold
  (feature 001) already set the JSX precedent, and a TS
  migration touches every file without changing behaviour.
- **Alternatives considered**: TypeScript for new files
  (rejected — mixed-language tree plus build changes for
  zero user-visible gain now; conversion tracked as follow-up
  work per constitution v1.4.0).

## Decision: Vitest + Testing Library + jsdom, Leaflet mocked at the adapter

- **Decision**: `vitest` with `@testing-library/react` and
  `jsdom`; a `test/setup.js` mocks the Leaflet map container
  so component tests assert logic (markers passed to the
  adapter, search behaviour, overlay states, dock
  inertness) without a real map. API calls are mocked at
  the `api/client.js` fetch wrapper.
- **Rationale**: Fast jsdom unit/component coverage of every
  acceptance scenario; the adapter boundary keeps map-library
  behaviour out of the assertions.
- **Alternatives considered**: Playwright end-to-end
  (rejected — heavyweight for an MVP with no backend
  coupling beyond fetch; revisit if cross-browser map
  behaviour needs proof); no frontend tests (rejected —
  overlay/empty/error states are exactly what regresses).

## Decision: One area at a time — debounced viewport, aborted stale requests, paged bbox fill

- **Decision**: Viewport changes are debounced (~300 ms);
  each new area request aborts the in-flight one
  (`AbortController`), and only the latest response renders.
  Bbox pages are followed through `total_pages` until the
  envelope's `count` is satisfied — safe because oversized
  areas return zero stops by contract, so page counts stay
  small. Markers always reflect exactly one area.
- **Rationale**: Directly implements the no-mixed-areas and
  never-partial rules (spec FR-003/FR-004, edge cases) with
  bounded request counts.
- **Alternatives considered**: Rendering page one only
  (rejected — silently partial markers, the exact failure
  FR-004 forbids); request-per-marker detail prefetch
  (rejected — bulk downloading by another name; details
  load on selection only).

## Decision: OSM tiles by default, attribution always, provider configurable

- **Decision**: Default tile URL
  `https://tile.openstreetmap.org/{z}/{x}/{y}.png` with
  `© OpenStreetMap contributors` attribution with the browser
  Referer as the identifying signal (no server-side tile fetching —
  library-default user agents get blocked), overridable via
  `VITE_TILE_URL` / `VITE_TILE_ATTRIBUTION`. Tiles load only
  for viewed zoom levels (the library default); no
  prefetching, no offline bundle.
- **Rationale**: Constitution stack rules verbatim; the env
  override is the configurable-provider setting it
  requires.
- **Alternatives considered**: Any other tile source as
  default (rejected — constitution fixes public OSM tiles
  for the small MVP); tile caching proxy (rejected — new
  infrastructure for a handful of users).

## Decision: Search over own data with debounce; no external lookup of any kind

- **Decision**: `SearchBox.jsx` debounces input (~300 ms)
  and queries the 003 routes/stops search through
  `api/client.js`; blank runs browse-all; no-match renders
  the spelling-or-browse hint. No Nominatim, no tile-server
  geocoding, no other external call exists in the search
  path — enforced by having a single client module with no
  external endpoints.
- **Rationale**: Spec FR-005 and the constitution's
  Nominatim ban, testable by traffic inspection (SC-002).
- **Alternatives considered**: Client-side filtering of a
  bulk download (rejected — bulk downloading contradicts
  the tile/data policy and breaks on dataset growth).

## Decision: Chat dock renders inert and provably quiet

- **Decision**: `ChatDock.jsx` renders the coming-soon
  label and a disabled-feeling entry control; activating it
  runs a no-op (no fetch, no storage, no state beyond the
  control itself). Its test asserts zero fetch calls and
  zero stored bytes on activation.
- **Rationale**: Reserves the 004 panel's home without
  shipping a control that pretends to work (spec Story 4).
- **Alternatives considered**: Omitting the dock until 004
  (rejected — 004 would then redesign the page instead of
  filling a slot); a live-looking disabled input (rejected —
  misleading; the coming-soon label must be explicit).

## Decision: Zero backend changes; the 003 API is used as-is

- **Decision**: No `backend/` edits of any kind. The UI
  consumes routes list/detail and stops list/detail
  envelopes exactly as contracted in 003 (including
  `zoom_in`/`empty` statuses); the one-page/overlay shape
  is pure client routing over those responses.
- **Rationale**: 003 already serves everything the map
  needs; touching the backend would reopen a finished,
  merged feature for no user-visible gain.
- **Alternatives considered**: A bespoke
  map-optimised endpoint (rejected — duplicates the 003
  contract and its tests); server-rendered pages
  (rejected — contradicts the React SPA stack).

