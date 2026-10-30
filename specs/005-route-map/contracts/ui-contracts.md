# Contract: UI Contracts

**Feature**: [spec.md](../spec.md) | **Date**: 2026-10-29

The address, API-usage, and tile/config contracts for the
one-page map UI. All transit payloads are the 003 read-API
envelopes, used exactly as contracted in
`specs/003-read-map-api/contracts/read-map-api.md` and never
reshaped here.

## Route addresses (react-router)

| Address | View | Behaviour |
|---------|------|-----------|
| `/` | Map-browse | Map, search, results; no overlay |
| `/routes/:id` | Map page + detail overlay | Overlay opens for that route; direct loads show the same state |
| any other path | Map-browse | Never an error page |

Unknown route ids and non-numeric segments resolve to the
overlay's plain-language not-found state, not to a routing
error.

## Read-API usage (003 envelopes, reused verbatim)

| UI need | Endpoint | Envelope handling |
|---------|----------|-------------------|
| Markers for area | `GET /api/v1/stops/?bbox=` | Follow `total_pages` until `count` satisfied; `zoom_in` → guidance, zero markers; `empty` → empty state |
| Search | `GET /api/v1/routes/?search=` and `GET /api/v1/stops/?search=` | Blank = browse-all (paged); matches link to overlay or centre the map |
| Stop selection | `GET /api/v1/stops/{id}/` | Coordinates + `serving_routes[]`; each route links to its overlay address |
| Route detail | `GET /api/v1/routes/{id}/` | Ordered `stops[]` with origin/terminus; `[]` → explicit no-stops statement; unknown id → plain not-found |
| Pagination | `page`, `page_size` | Default 20, cap 100; beyond-end pages are empty with correct totals |

Invalid values and failures surface the API's plain-language
errors in place; no technical details are ever rendered.

## Tile and provider configuration

| Setting | Default | Meaning |
|---------|---------|---------|
| `VITE_TILE_URL` | `https://tile.openstreetmap.org/{z}/{x}/{y}.png` | Public tile template (constitution) |
| `VITE_TILE_ATTRIBUTION` | `© OpenStreetMap contributors` | Required attribution, always rendered |

Tiles load for viewed zoom levels only. No prefetching, no
offline bundle, no alternate default source. The map library
sits behind `MapView.jsx` alone; swapping providers touches
only that module. The recorded alternative is MapLibre GL JS
(`maplibre-gl`, BSD-3-Clause) — not Mapbox GL JS (proprietary,
token-billed); a future swap additionally needs a vector tile
source decision.

## Component contracts (props in, callbacks out)

- `MapView`: in — markers, highlight, tile config; out —
  debounced area changes. Never fetches transit data
  itself.
- `SearchBox`: in — nothing (owns its input); out —
  debounced query strings. No external calls.
- `ResultsList`: in — route/stop candidates + states
  (loading, empty, no-match, error) plus journey content;
  out — selections and tab changes.
- `RouteOverlay`: in — route detail payload or
  loading/empty/not-found state; out — dismiss.
- Journey tab content (004): the journey panel; out — nothing
  to the rail (it calls the journey endpoints itself).
- `api/client.js`: the single module allowed to call the
  read API; every other module receives data as props.

## Non-goals (explicitly out of contract)

- Accounts, history, favourites, or any persistence.
- Schedules, times, transfers, AI, voice, feedback.
- Server-side rendering or backend changes of any kind.
- Any external place-search, geocoding, or tile source.

