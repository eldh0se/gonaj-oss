# Data Model: Read Map API

**Feature**: [spec.md](spec.md) | **Date**: 2026-10-29

No new tables. This feature is a read projection over the dataset
imported by `specs/002-osm-snapshot-import`. Each public entity
below names the stored source, the fields exposed, the fields
structurally hidden, and the validation/serving rules. Field shapes
are normative in [contracts/read-map-api.md](contracts/read-map-api.md).

## Serving rules (apply to every entity)

- **Servable routes**: `Route.quarantined = False` AND the route
  belongs to a `RouteMaster` via `RouteMasterMembership`. All other
  routes (quarantined, orphan, blocked-master) are indistinguishable
  from unknown ids: plain-language 404 (research Decision 3).
- **Servable stops**: every imported `Stop` row.
- **Identity**: the public `id` is the stored row's surrogate `id`.
  (`osm_type`, `osm_id`) are provenance and are never exposed.
- **Provenance hidden, never discarded**: `import_run`, snapshot,
  recipe, OSM identifiers, and `Stop.tags` stay stored (Principle V)
  and are absent from every response (FR-007).

## Route (public view) — source: `Route` + its `RouteMaster`

One direction/variant of a bus service as passengers see it.

- Exposed: `id`, `name` (nullable in storage; exposed as stored),
  `origin` (from `from_text`), `destination` (from `to_text`),
  `operator` and `network` (read through the route's master;
  `null` when the master carries none).
- Hidden: `osm_type`, `osm_id`, `import_run`, `verdict`,
  `quarantined`, `direction`, the master object itself, all tags
  and provenance.
- Relationships: served stops via `RouteStopMembership` ordered by
  `position`; master via `RouteMasterMembership` (filter/join only,
  never serialised).
- Validation: list search matches `name`, `from_text`, `to_text`,
  and served stop names (`Stop.name`, `Stop.name_ml`,
  case-insensitive containment); `operator`/`network` filters are
  exact stored-value matches; blank search = browse-all (FR-004,
  FR-005).
- Ordering/duplicates: master-membership position, then `id`;
  stored duplicates are preserved (FR-006).

## Stop (public view) — source: `Stop`

One boarding/alighting place.

- Exposed: `id`, `name` (nullable; exposed as stored), `name_ml`
  (nullable), `lat`, `lon`. Detail additionally exposes
  `serving_routes[]` (route `id` + `name` per serving servable
  route, ordered as in the routes list).
- Hidden: `osm_type`, `osm_id`, `import_run`, `tags`.
- Relationships: serving routes via `RouteStopMembership` (only
  servable routes are listed; a stop served only by withheld routes
  shows an explicit empty list, FR-012).
- Validation: text mode matches `name`/`name_ml` by
  case-insensitive containment; bbox mode filters
  `min_lon ≤ lon ≤ max_lon` AND `min_lat ≤ lat ≤ max_lat` (closed
  bounds); the two modes are mutually exclusive (FR-008, FR-009).
- Ordering: `name`, then `id`. Coordinates are always present in
  detail (storage requires them, 002).

## Route Stop (ordered step) — source: `RouteStopMembership`

One stop's place in one route's travelling sequence. Appears only
inside route detail.

- Exposed: `stop` (`id`, `name`, `name_ml`, `lat`, `lon`),
  `position` (1-based, contiguous per 002), `is_origin`
  (`position` = first), `is_terminus` (`position` = last). A
  single-stop route is both origin and terminus.
- Hidden: `source_index`, `import_run` (internal order provenance;
  `position` is the public order).
- Validation: ordered by `position` ascending (FR-013); a route
  with no memberships serialises `stops` as `[]`, explicitly
  (FR-014). Duplicate platform entries appear as separate steps in
  stored order — never deduplicated (002).

## Connectivity Result — derived, not stored

One direct-connection claim joining two `RouteStopMembership` rows
on the same servable route.

- Exposed: the route (`id`, `name`, `origin`, `destination`,
  `operator`, `network`), `from_position` and `to_position` (the
  two stops' positions on that route), and `evidence`
  (`/api/v1/routes/{id}/`).
- Derivation rule: same route, both stops present,
  `from_position < to_position`; each matching route appears once
  (FR-016, FR-017).
- Absent by construction: times, durations, frequencies, transfers
  (FR-018). No matching route = empty envelope, not an error.

## Deliberately absent

No `Trip`, `StopTime`, or `ServiceCalendar` reads (Principle VIII —
schedule data does not exist yet); no `Feedback` surface (later
feature); no master, snapshot, run, anomaly, or provenance reads of
any kind (internal/Admin-only per Principles V/VII).

