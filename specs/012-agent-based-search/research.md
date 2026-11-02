# Research: Agent-Based Area Search for Direct Journeys

**Feature**: [012-agent-based-search](./spec.md) | **Date**: 2026-11-01

Phase 0 output. Every planning-time value the spec defers is decided here with
rationale and rejected alternatives. All findings are grounded in the current
code (`backend/apps/journey/tools.py`, `backend/apps/journey/agent.py`) and the
feature's dev-notes (`dev-notes/agent_loop.md`, `dev-notes/agent_tools.md`,
`dev-notes/agent_instructions.md`).

## Decision 1: Pair-cap value — 200 pairs, nearest-first

- **Decision**: The matrix test evaluates at most **200 origin×destination pairs**,
  ordered by ascending minimum member-to-member haversine distance across the
  two ends (clarify outcome B). Pairs beyond 200 are untested (farther first)
  and count as "pairs went untested" for the refuse-vs-pick rule.
- **Rationale**: Same-name groups are small in practice (the spec's Kaloor shape
  is 3+2 members; the existing `search_places` pre-grouping cap is
  `RESULT_LIMIT = 100` per side in `tools.py`). 200 covers combinations like
  10×20 or 14×14 without truncation. Each empty pair costs exactly one indexed
  route-filter query (`_direct_pair_routes` returns before the membership query
  when no route serves both stops), so 200 pairs stay within a synchronous
  request budget on the simple stack (constitution VI). Member lat/lon are
  already in hand from `search_places`, so ordering costs no extra queries
  (pure-Python haversine via the existing `_haversine_m`).
- **Alternatives considered**:
  - Per-side member cap (e.g. 20 nearest members per end): rejected — drops
    near members of genuinely large groups (a 100-member origin cluster would
    lose served boarding stops) while still allowing 400 pairs.
  - Unlimited pairs: rejected — worst case 100×100 = 10,000 pairs × up to 2
    queries each is unacceptable DB load per request.
  - Lower total cap (e.g. 50): rejected — truncates legitimate 10×10 near
    clusters and would force pick prompts where direct answers exist.

## Decision 2: Mates-per-route cap — 3 nearest + overflow count

- **Decision**: The walk note names at most the **3 nearest** walkable mates per
  end; when more mates qualify (`d <= 150m`), the note appends
  `plus {N} more within 150m`.
- **Rationale**: The canonical defect case is opposite-side pair + one extra
  mate (K1/K2 + K3): 3 covers both sides of the road plus one. Full
  enumeration turns noisy on dense corridors; a hard cap of 1 would hide the
  opposite side — the exact information this feature exists to surface.
  The overflow count keeps the note honest without the noise.
- **Alternatives considered**:
  - All mates: rejected — noisy on dense corridors, harms small-screen
    readability of the per-route answer.
  - 1 mate: rejected — hides opposite-side duplicates, the core defect.

## Decision 3: Walk-note prose template

- **Decision**: Per cited route, the answer prose is:
  `Take the {route_name} service from {boarding_name} to {alighting_name}, see /routes/{route_id}.`
  followed, for each end that has mates, by
  ` Also near {end_name}: {mate_name} ({walk_m}m walk)[, ...][ plus {N} more within 150m].`
  `walk_m` is whole meters (rounded). Multi-destination answers join one such
  block per destination (existing `rank_pairs` sentence pattern).
- **Rationale**: Extends the dev-notes answer shape and the existing
  `rank_pairs` prose (`Take the ... service from ... to ..., see ...`) with
  the walk note, keeping one citation + one note per route. Whole meters match
  the imprecision of a walking estimate.
- **Alternatives considered**:
  - Tabular/structured-only note: rejected — the journey answer is prose for
    passengers (structured `also_nearby` already rides in the payload options).
  - Exact float meters: rejected — false precision for a walk estimate.

## Decision 4: `nearby_stops` max radius — 2000m (default 500m)

- **Decision**: `nearby_stops(lat, lon, radius_m)` defaults to `radius_m = 500`,
  enforces a maximum of **2000m**, returns at most 100 stops ordered by
  ascending `distance_m`, and returns `{"ok": False, "error": ...}` for invalid
  coordinates or radius above the maximum. Implementation is a DB bbox
  prefilter (±radius degrees approx.) plus pure-Python haversine filtering via
  the existing `_haversine_m` — SQLite-portable, no PostGIS (same pattern as
  `_cluster_rows`).
- **Rationale**: Beyond ~2km a stop is not a "nearby" boarding point, and an
  unbounded radius degenerates the bbox prefilter into a table scan. 2000m
  leaves headroom above the 500m default for the next feature's far-stop
  search while staying selective. The dev-notes' "same zoom_in guard as
  stop search" is not adopted: `zoom_in` is a bbox-span guard and a
  point-radius query has no span — the spec's max-radius rule replaces it.
- **Alternatives considered**:
  - No maximum: rejected — unbounded radius risks full-table scans.
  - Maximum = default (500m): rejected — leaves no room above the default for
    the next feature's wider searches.

## Decision 5: Reuse over new code

- **Decision**: Reuse, in this order:
  - `_haversine_m` (`EARTH_RADIUS_M = 6371000.0`) for `distance_m` (thin
    float-validating wrapper) and `nearby_stops` filtering.
  - `servable_routes` / `routes_with_master_fields` /
    `routes_with_endpoint_names` / `order_routes` inside `nearby_stops` only
    where route hints are needed (stops list itself needs no route joins).
  - `_direct_pair_routes` (single source of `pos_from < pos_to` truth) —
    `find_routes_matrix` already delegates to it; no logic change.
  - `_verify_route` + `_FORBIDDEN_SHAPED` + one-repair-retry loop unchanged as
    the server verifier (Step 6 of the loop).
  - `_rank_pairs` grouping by operator + `(stop_count, route_id)` ordering +
    5-destination cap with overflow count: reused for the ranked answer,
    extended so each option carries `also_nearby`.
  - `dev-notes/agent_instructions.md` becomes the new `SYSTEM_PROMPT`
    (group-first rules, walk-note shape, refuse codes); `find_routes`
    mention replaced with the matrix path per FR-011.
- **Rationale**: Smallest diff on the read-only stack; every reused helper is
  already covered by journey tests.
- **Alternatives considered**:
  - PostGIS `ST_DWithin` for `nearby_stops`: rejected — breaks the
    SQLite-portable test path the journey suite relies on (factories +
    stubbed provider, no live Postgres needed for unit runs).

## Decision 6: No-bypass mapping (FR-011)

- **Decision**: Old path → new path:
  - `_resolve_selection` "full" (both ids known) → ids enter the matrix flow
    as singleton member sets; `answer_direct` stays only as the leaf
    verifier for that verified single pair, never as the entry answer.
  - `_resolve_selection` "partial" + `_remaining_from_question` (single-stop
    `search_stops` derivation) → other end derived via `search_places`
    groups; singleton group is the degenerate case, not a shortcut.
  - `_disambiguation_context` regex-gated flat-stop payloads → group-based
    payloads built from `search_places` results (`slot`, `offered_ids`,
    `resolved`, `slots` unchanged in shape, members grouped).
  - `find_routes` remains wired for the leaf verifier and familiar-user
    direct search; it MUST NOT answer inside `run_journey` (FR-011). Per the
    clarify outcome, when no viable pair exists the helper may *suggest*
    direct from-to search but must not run it as the answer.
- **Rationale**: The wrong-side defect lives exactly in these four bypasses
  (verified in code: exact-id `answer_direct` refuses without ever trying
  group mates). Replacing entry flow while keeping the verifier preserves
  011's exact-stop tap semantics (a tap selects a member id; verification
  still proves it) without breaking familiar-user direct search, which 011
  explicitly blesses as a user-invoked path.
- **Alternatives considered**:
  - Delete `answer_direct` entirely: rejected — contradicts 011 (explicit
    exact picks still need a leaf verifier; direct search stays available
    as a user-invoked path).

## Decision 7: Inexact intent check as a same-place allowlist (FR-013)

- **Decision**: Inexact (`exact` False) ends never auto-answer. The top 5
  groups with scores go to the model as a same-place allowlist with generic
  place-identity wording: keep only the same place the passenger asked for,
  reject any different place even with token overlap. The model returns
  `KEEP <ids>` for same-place members only, or `REJECT <ids>` for different
  places; only `KEEP` ids are kept and every other listed member is dropped
  (a bare `ACCEPT` keeps nothing unless ids are listed). When two groups are
  the same place, both are kept for matrix ranking. Dropped members join the
  excluded set and `search_places` retries with `exclude_ids`, bounded at 3
  attempts per end, then refuses or picks per FR-007.
- **Rationale**: Token overlap alone never proves sameness: similar names
  routinely belong to different places, so a reject-list tied to any one
  naming pattern (compass words, station suffixes, or any other similarity)
  would miss the next near-miss. A keep-list built on place identity is
  generic: the model keeps what matches the request and everything else is
  dropped, so no per-pattern logic can go stale.
- **Alternatives considered**:
  - Reject-list with per-pattern wording: rejected — each new similarity
    shape needs new wording; the allowlist covers all of them with one rule.
  - Auto-answer the top-ranked fallback group: rejected — the top score can
    still be the wrong place; FR-013 forbids auto-answering inexact ends.

## Deferred (out of scope, noted for the next feature)

- Map-area (`bbox`) ends in the deterministic flow: `bbox` exists in
  `TOOL_SCHEMAS` and the validator for model-loop use; wiring `bbox` ends
  with relevance paging into the group-first flow is the next feature.
- Location variant (loop Step 1b: origin ids from `nearby_stops` instead of
  `search_places` query): `nearby_stops` is created now; its consumption is
  the next feature. `FR-001` forbids live location overriding a named end.
- Far-group onward walk-plus-routing (walk 500m to a corridor from kaloor#2):
  matrix still tests far-group members for direct routes; no onward leg is
  constructed.
- Single-ended questions keep legacy behavior (spec Assumptions).
