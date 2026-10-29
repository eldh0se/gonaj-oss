# Data Model: Route Map

**Feature**: [spec.md](spec.md) | **Date**: 2026-10-29

No backend entities and no new tables. Everything below is
transient client-side UI state; all transit facts come from
the 003 read API per request and are never stored. Shapes of
API payloads are normative in `specs/003-read-map-api` and
are referenced, not duplicated, in
[contracts/ui-contracts.md](contracts/ui-contracts.md).

## Map View (transient page state)

The one page's state.

- Carries: current area (bounds), the marker set for exactly
  that area, the search state, the open overlay route id (or
  none, synced with the `/routes/:id` address), and the chat
  dock region.
- Validation: marker set is replaced wholesale on every area
  change (never merged); a newer area response discards any
  older in-flight one; on unmount/leave nothing persists.
- Relationships: markers derive from the stops list envelope;
  the overlay derives from the route detail response; the
  search derives from the routes/stops search responses.

## Stop Marker (transient, derived)

One rendered stop.

- Carries: stop `id`, name, coordinates (as served), and the
  serving-route references shown on selection.
- Validation: every marker corresponds to a stop inside the
  current closed-bound area; edge stops included; zero
  markers rendered with guidance shown for oversized areas.

## Route Detail Overlay (transient, derived)

One opened route.

- Carries: route fields (name, origin, destination,
  operator, network), ordered stops with origin/terminus,
  the map highlight, and the `/routes/:id` address.
- Validation: empty membership renders the explicit
  no-stops statement; unknown id renders the plain-language
  not-found state; direct navigation to the address opens
  the same overlay.
- State transitions: closed → open (selection or address)
  → closed (dismiss returns to map-browse, address back to
  `/`).

## Search (transient request state)

One text query.

- Carries: the query text and the candidate results (routes
  with detail links, stops with centre-on-pick).
- Validation: blank means browse-all (paginated); no match
  is the explicit hint message; queries hit the
  application's own endpoints only.

## Deliberately absent

No user accounts, profiles, history, favourites, or cached
tiles/data beyond the library's in-memory map rendering. No
schedule, trip, feedback, AI, voice, or tracking entities of
any kind in this feature. No backend tables, migrations, or
endpoint changes.

