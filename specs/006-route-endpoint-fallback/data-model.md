# Data Model: Route Endpoint Fallback

**Feature**: [spec.md](spec.md) | **Date**: 2026-10-29

No schema change. No new entities, no new tables, no
migrations. Everything below is derived at request time
from entities owned by 002/003.

## Resolved endpoint (derived, not stored)

- **Source**: `RouteStopMembership` rows of the route,
  ordered by `position` (the same ordering the detail view
  already uses to mark `is_origin` / `is_terminus`).
- **resolved_origin**: name of the first ordered stop's
  `Stop.name`; `resolved_destination`: name of the last.
- **Precedence**: non-blank stored `from_text` / `to_text`
  always wins; null, empty, and whitespace-only stored
  text count as absent.
- **Validation**: a route with no memberships resolves to
  null/null (explicit, never invented); a single-stop
  route resolves to the same name twice; a null stop name
  resolves to null for that side.
- **Lifecycle**: computed per request, never written back;
  `from_text` / `to_text` stay exactly as imported.

## Untouched entities

`Route`, `Stop`, `RouteStopMembership`,
`RouteMasterMembership`, `Agency`, `Trip`, `StopTime`,
`ServiceCalendar`, `Feedback`, `Source`, `ImportRun`,
`OsmSnapshot` — no field, constraint, or index changes.
Provenance rules from the constitution apply unchanged,
and no hidden field (`tags`, `osm_*`, masters, provenance)
reaches the responses through the fallback.

