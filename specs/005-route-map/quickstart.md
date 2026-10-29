# Quickstart: Route Map

**Feature**: [spec.md](spec.md) | **Date**: 2026-10-29

Validates the one-page map UI end to end against
[contracts/ui-contracts.md](contracts/ui-contracts.md).
Backend behaviour is the already-merged 003 read API; this
guide proves the UI, not the API. Examples assume the server
from `docs/setup-backend.md` with the imported dataset loaded,
and the frontend dev server proxying `/api` to it.

## Prerequisites

- Backend serving per `docs/setup-backend.md` (database up,
  migrations applied, `createcachetable` done) with the
  dataset imported per `specs/002-osm-snapshot-import`.
- Frontend dependencies installed (`npm install` in
  `frontend/`); dev server via `npm run dev`.
- No credentials anywhere; no tile key needed.

## 1. Browse the map (Story 1)

1. Open `/` over an area with known stops — expect each
   in-area stop rendered once as a marker, each leading to
   its serving routes.
2. Pan and zoom rapidly — expect markers to settle on
   exactly the latest area with no mixed-area leftovers.
3. Zoom out to a state-sized area — expect zero markers
   plus zoom-in guidance, never a partial set.
4. Pan to an empty area — expect the explicit empty state,
   not an error.
5. Stop the backend and reload — expect the
   plain-language cannot-load message, not a broken map.

## 2. Search (Story 2)

1. Type a known route-name fragment — expect only matching
   routes, each opening the detail overlay.
2. Type a known stop-name fragment — expect only matching
   stops; picking one centres the map on it.
3. Clear the search — expect the full browse list
   (paginated).
4. Search a nonsense string — expect the plain no-match
   message with the spelling-or-browse hint.
5. Open devtools network while searching — expect calls
   only to the application's own `/api/v1/*` endpoints,
   never to any external place search.

## 3. Route detail overlay (Story 3)

1. Open a route from search — expect name, origin,
   destination, operator, ordered stops with marked origin
   and terminus, and the route highlighted on the map.
2. Copy the address (`/routes/:id`), open it directly in a
   new tab — expect the same map page with the same
   overlay open.
3. Open a route with no recorded stops — expect success
   with the explicit no-stops statement.
4. Open `/routes/99999999/` — expect the plain-language
   not-found state inside the overlay, map still usable.

## 4. Chat dock (Story 4)

1. Load `/` — expect the chat dock region present, labelled
   as the future journey helper and marked coming soon.
2. Activate its control with devtools network open —
   expect zero requests, zero stored bytes, and the plain
   not-available message.

## 5. Small screens and tiles

1. Narrow to a phone-width viewport — expect single-column
   reflow with every control reachable and no horizontal
   scrolling.
2. Block tile imagery (offline devtools) — expect markers,
   search, and overlay to keep working over a plain
   background with the imagery notice shown.

## Automated suite

Run the frontend tests (`npm test` in `frontend/`):
component tests for map/search/overlay/dock states via
Testing Library with the Leaflet container mocked;
no-network contract tests for the `api/client.js` envelope
handling (`zoom_in`/`empty`/caps/errors).

## Done when

All five steps succeed, the automated suite is green, and
review confirms zero backend changes, zero external
place-search calls, zero accounts or tracking, and public
tiles with attribution throughout.

