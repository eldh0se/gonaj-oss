# Data Model: Agent-Based Area Search for Direct Journeys

**Feature**: [012-agent-based-search](./spec.md) | **Date**: 2026-11-01

Phase 1 output. **No schema change, no migration.** This feature reads the
existing canonical tables and adds transient (in-answer) structures only.

## Existing entities (unchanged)

All live in `backend/apps/transport/models.py`, read via the 003 query helpers
(`servable_routes`, `routes_with_master_fields`,
`routes_with_endpoint_names`, `order_routes`).

- **Stop**: `{id, name, name_ml, lat, lon, ...}` plus provenance. Grouping key
  is `name.casefold()` (see `_normalized_place_name`); `name_ml` participates
  in matching (`icontains` over both).
- **Route** (servable subset): `{id, name, origin, destination, operator,
  network, evidence=/routes/:id}`. Only servable routes ever cite.
- **RouteStopMembership**: `{route, stop, position}`. The single source of
  travelling-order truth: a pair is viable iff both stops share one servable
  route with `pos_from < pos_to` (enforced in `_direct_pair_routes`,
  re-checked by `_verify_route`).

## Transient structures (new, in-answer only)

- **ViablePair**: `{from_stop_id, to_stop_id, route_id}`. Produced by
  `find_routes_matrix`; never persisted. Validation: ids positive ints,
  `from != to`, both known stops, route servable with `pos_from < pos_to`.
- **ClassifiedRoute**: `{route, direct_from_id, direct_to_id,
  nearby_from[{id, walk_m}], nearby_to[{id, walk_m}]}`. `direct_*` are the
  matrix-tested members; `nearby_*` are same-group members with
  `distance_m(direct, mate) <= 150.0` via `_haversine_m`
  (`R = 6371000.0`, inclusive boundary), at most 3 nearest per end with an
  overflow count (`plus {N} more within 150m`). `walk_m` is whole meters.
- **Walk distance**: pure function of two coordinates; no stored state.

## Validation rules (enforced where)

| Rule | Enforced in |
|------|-------------|
| Exactly one of `query`/`bbox` per search call | `search_places` (existing, unchanged) |
| `empty` → pick prompt; `zoom_in` → narrow-or-map-prompt | `run_journey` fallback (FR-012) |
| Pair cap 200 (`MATRIX_PAIR_CAP`), nearest-first by min member distance, `truncated` + `untested_from/to_ids` in result | `find_routes_matrix` (tool-side ordering); agent passes `limit` and routes truncation to the pick payload (research Decision 1) |
| `d <= 150m` inclusive via haversine, `R = 6371000.0` | classification step (`distance_m`) |
| ≤3 mates per end + overflow count; whole-meter `walk_m` | answer builder (research Decisions 2–3) |
| ≤5 destinations, ranked operator → stop_count → route_id | `rank_pairs` (existing cap reused) |
| `nearby_stops`: default radius 500m, max 2000m, ≤100 stops, ascending `distance_m`, error on bad input | new tool (research Decision 4) |
| Every citation re-checked via `get_route_detail`, `pos_from < pos_to`, `_FORBIDDEN_SHAPED` clean, one repair retry | existing server verifier (unchanged) |
| No single-pair `find_routes` answer inside `run_journey` | entry-flow replacement (research Decision 6) |

## State transitions

None: all tools are read-only; the journey answer is computed per request
from current canonical data. Selection `context` (`candidate_stop_ids`,
`slot`, `selected_stop_id`, `resolved`, `slots`) keeps its existing shape —
a pick selects a member id only and enters the same matrix flow (FR-011).
