# Implementation Plan: Route Map

**Branch**: `005-route-map` | **Date**: 2026-10-29 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/005-route-map/spec.md`

## Summary

The single-page map UI: a Leaflet map rendering stops and
routes from the 003 read API, text search over the application's
own data, a route detail overlay deep-linked at `/routes/:id`
(the destination the 004 journey helper's evidence links
require), and an inert coming-soon chat dock reserving the 004
panel's home. No backend changes — this feature reads the
existing versioned API only. See [research.md](research.md) for
decisions and rationale.

## Technical Context

**Language/Version**: JavaScript (JSX, matching the scaffolded
`main.jsx`), React 18.3, Vite 6 (existing scaffold, unchanged
toolchain).

**Primary Dependencies** (new, all client-side libraries — no
services): `leaflet` (map rendering, constitution-mandated),
`react-router-dom` (deep-linkable `/routes/:id` overlay address),
dev-only `vitest` + `@testing-library/react` + `jsdom`
(component tests). No other new packages.

**Storage**: None client-side beyond in-memory UI state. All
transit data comes from the 003 read API per request; no
caching layer, no local persistence.

**Testing**: `vitest` with Testing Library and jsdom; Leaflet
map container mocked at the adapter boundary; API calls mocked
at the `api/client.js` fetch wrapper.

**Target Platform**: Responsive web frontend (desktop and small
screens, single-column reflow); the existing Vite dev proxy
forwards `/api` to the Django backend in development.

**Project Type**: Frontend web application addition inside the
monorepo (`frontend/` only; zero backend changes).

**Performance Goals**: Marker sets track exactly one map area:
viewport changes are debounced, in-flight stale area requests
are discarded, and bbox pages are followed only for small
areas (oversized areas return zero stops by contract). No tile
prefetching or bulk downloading.

**Constraints**: Public OSM tiles only with attribution and a
configurable provider setting; no Nominatim or external place
search ever; no login, accounts, or tracking; map provider
integration isolated behind one adapter module (MapLibre GL JS
(`maplibre-gl`, BSD-3-Clause — not `mapbox-gl`) is the recorded
alternative); single-column small-screen layout
with every control reachable.

**Scale/Scope**: MVP audience. One page, two views (map-browse
+ route detail overlay), search, inert chat dock. No AI, voice,
feedback, or schedule UI in this feature.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I (MVP validation first)**: PASS — browsable route/stop
  discovery is the narrowed validation question itself.
- **II (read-only public product)**: PASS — reads the 003 API
  only; no editing, feedback, or data-entry surface.
- **III (no accounts, minimal data)**: PASS — no login, no
  tracking, no per-user state; public tile requests are the
  constitution-permitted tile service with attribution.
- **IV (monorepo separation)**: PASS — frontend consumes only
  the versioned REST boundary (plus the dev proxy, which is
  tooling, not coupling).
- **V (app-owned data + provenance)**: PASS — all transit data
  from the owned API; provenance untouched and unexposed.
- **VI (simple stack, deferred complexity)**: PASS — client
  libraries only (map, router, test runner); no services,
  queues, routing engines, or journey planners. No new
  backend, database, or deployment component of any kind.
- **VII (Django Admin)**: PASS — no data operations in this
  feature at all.
- **VIII (schedule gating)**: PASS — no times, timetables, or
  schedule UI anywhere.
- **IX (Meta AI)**: PASS — no AI in this feature. The chat
  dock is specified inert (zero requests, zero storage), and
  evidence links point at the route addresses this feature
  builds.

Post-design re-check: no new principles engaged; all gates
still pass. No violations to justify — Complexity Tracking
intentionally empty.

## Project Structure

### Documentation (this feature)

```text
specs/005-route-map/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── ui-contracts.md  # Route addresses, API usage, tile/config contract
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
frontend/
├── package.json                   # EXTEND: leaflet, react-router-dom, vitest + testing-library/jsdom (dev)
├── src/
│   ├── main.jsx                   # REWRITE: router root (was scaffold placeholder)
│   ├── App.jsx                    # NEW: one-page layout (map + overlay + dock slot)
│   ├── api/
│   │   ├── client.js              # NEW: fetch wrapper for 003 routes/stops/route-detail (+ errors)
│   │   └── tiles.js               # NEW: tile provider config (OSM default, attribution, env override)
│   ├── components/
│   │   ├── MapView.jsx            # NEW: Leaflet adapter (provider-isolated), markers, viewport callback
│   │   ├── SearchBox.jsx          # NEW: debounced text search over own data
│   │   ├── ResultsList.jsx        # NEW: route/stop candidates, browse-all, empty/no-match states
│   │   ├── RouteOverlay.jsx       # NEW: ordered stops, origin/terminus, empty/not-found states
│   │   └── ChatDock.jsx           # NEW: inert coming-soon dock (zero requests, zero storage)
│   └── test/
│       └── setup.js               # NEW: vitest/jsdom setup, Leaflet container mock
└── (no backend changes: apps/, config/ untouched)
```

**Structure Decision**: All new code lives under `frontend/src/`
in `api/` (boundary clients), `components/` (one module per
spec view), and `test/` (harness setup) — mirroring the domain
split of the spec's user stories. `main.jsx` is rewritten
because the scaffold placeholder it holds is explicitly marked
for replacement by the first transport feature. The map
provider sits behind `MapView.jsx` alone so a Leaflet→MapLibre GL JS
swap touches one module. Zero backend changes: every byte of
transit data arrives through the existing versioned API.

## Complexity Tracking

> No constitution violations — nothing to justify. Table intentionally omitted.
