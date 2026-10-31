# Research: Place Groups for Same-Named Stops

**Feature**: [spec.md](spec.md) | **Date**: 2026-10-31 | **Branch**: `009-place-groups`

No NEEDS CLARIFICATION remained: the requester fixed the slice (Django + PostGIS-ready Postgres, reuse `servable_routes`/`order_routes`/`RouteStopMembership.position`; `tools.py` gains `search_places` + `find_routes_matrix`; keep `RESULT_LIMIT 100` and `MAX_BBOX_SPAN_DEGREES 0.5`; no model changes; Kaloor 2-group + opposite-direction tests). Each decision below records what was chosen, why, and what was set aside.

## Decision: Normalize by casefolded name, cluster single-linkage within 150 m haversine in Python

- **Decision**: Group key is `(name.casefold().strip(), cluster_index)`. Within one normalized name, order stops by `(name, id)`, seed the first unassigned stop, and absorb every unassigned stop within 150 m haversine of any cluster member (single-linkage), then repeat. Deterministic for unchanged data.
- **Rationale**: Case-insensitive matching catches `KALOOR`/`Kaloor `/name_ml-adjacent duplicates without extra queries; single-linkage chains the normal opposite-side pairs (a few meters apart) while a hard 150 m gap splits far-apart same-named places into separate groups per FR-006. Pure-Python haversine keeps the code SQLite-portable for the test gate (no PostGIS functions, no new dependency).
- **Alternatives considered**: DB-level PostGIS `ST_ClusterDBSCAN` (rejected — the app runs on the plain `postgresql` backend and tests must stay SQLite-portable; would also add a migration/extension dependency for a read-time grouping); exact-coordinate grouping (rejected — opposite-side duplicates differ by meters and would never group).

## Decision: 150 m cluster radius

- **Decision**: Two stops join one place group when linked by ≤150 m hops.
- **Rationale**: Requester-fixed; matches a recognizable walking cluster (a bus station and its opposite-side boarding points span tens of meters; distinct same-named localities in Kochi lie far further apart). Recorded here as the assumption the spec deferred to plan time.
- **Alternatives considered**: Smaller radius (rejected — risks splitting genuine opposite-side pairs); larger radius (rejected — risks merging distinct places, the exact failure FR-006 forbids).

## Decision: Group shape carries `spread_m` and capped `routes` alongside the requested fields

- **Decision**: `groups[{key, label, center, bbox, spread_m, members[{id,name,lat,lon}], route_count, routes[{id,name}]}]`. `spread_m` is the max pairwise haversine distance between members in meters (0 for singles). `routes` lists serving routes ordered by name, capped at 10; `route_count` is the uncapped total.
- **Rationale**: The requested shape (`route_count` only, no spread) under-serves spec FR-004/FR-005 (spread in meters, route hints passengers can match to their bus). `spread_m` makes FR-006 testable; the capped list keeps payloads bounded while `route_count` stays exact.
- **Alternatives considered**: Requested shape verbatim (rejected — spec compliance needs spread + usable hints); uncapped route lists (rejected — a central hub group could dump dozens of routes into one payload).

## Decision: `find_routes_matrix` reuses `find_routes` pair logic, keeps only travelling-order pairs

- **Decision**: For each `(from_id, to_id)` with `from_id != to_id`, run the same servable-route + ordered-membership + `position[from] < position[to]` check as `tools.find_routes` (shared helper, not a copy); return only pairs with ≥1 direct route, each with `/routes/:id` evidence. Opposite-direction pairs drop out naturally.
- **Rationale**: One definition of "direct service" instead of two (same reuse principle as 004); the matrix is what group-to-group journey resolution needs next without any model involvement.
- **Alternatives considered**: A single bulk SQL join across all pairs (rejected — harder to keep byte-identical semantics with `find_routes`; pair count is bounded by group sizes); returning empty pairs (rejected — noise; callers only need viable pairs).

## Decision: Mirror `search_stops` bbox/query semantics and limits

- **Decision**: `search_places(query=None, bbox=None)` accepts exactly one of the two; oversized bbox returns `zoom_in` with zero groups; empty areas return `empty`; results cap at `RESULT_LIMIT 100` stops before grouping.
- **Rationale**: Same contract shape passengers and reviewers already know from 003/004; capping pre-grouping bounds the Python clustering work.
- **Alternatives considered**: Separate limits for places (rejected — one limit, already understood); allowing query+bbox together (rejected — matches the existing `search_stops` error).

## Decision: Tools-only slice — no model, endpoint, or agent wiring in 009

- **Decision**: 009 adds the two pure functions plus tests and shape contracts. No new model tool registration, no prompt changes, no REST endpoint, no `agent.py` wiring.
- **Rationale**: Requester-fixed ("No model changes"); keeps the slice reviewable and independently testable. Spec FR-008 (journey choice uses groups) is recorded as the follow-up consumer with `find_routes_matrix` as its ready-made engine.
- **Alternatives considered**: Registering `search_places` as a fourth model tool now (rejected — model-surface change contradicts the brief); adding `GET /api/v1/places/` now (rejected — endpoint design deserves its own contract review; the shape contract here is written endpoint-ready).
