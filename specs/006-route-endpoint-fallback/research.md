# Research: Route Endpoint Fallback

**Feature**: [spec.md](spec.md) | **Date**: 2026-10-29

No NEEDS CLARIFICATION remained: scope (runtime fallback,
all three shapes, stored-text precedence, no invention) was
settled with the user before specifying. Each decision below
records what was chosen, why, and what was set aside.

## Decision: One shared annotation helper, not three payload-site copies

- **Decision**: Add a `routes_with_endpoint_names`-style
  helper beside `routes_with_master_fields` in
  `backend/apps/transport/api/views.py`, annotating
  `resolved_origin` / `resolved_destination` per route via
  correlated `Subquery`s on `RouteStopMembership` ordered
  by `position` (first and last). All three views
  (`route_list`, `route_detail`, `connectivity`) apply the
  helper; payloads read the annotation.
- **Rationale**: One precedence rule in one place — the
  card/detail/evidence agreement the spec demands cannot
  drift between copies. Mirrors the established master-fields
  annotation pattern, including T036's DISTINCT-safe shape
  (annotations are selected outputs).
- **Alternatives considered**: Per-site Python fallback
  (rejected — three copies of the precedence rule; list
  view would need an extra round-trip query per page);
  import-time backfill of `from_text`/`to_text`
  (rejected — rewrites stored source data and needs a
  reimport; the spec requires runtime derivation with
  stored text winning).

## Decision: Coalesce(NullIf(Trim())) precedence in the database

- **Decision**: `resolved_origin = Coalesce(NullIf(Trim(
  "from_text"), Value("")), endpoint_origin_subquery)`
  (and mirror for destination), so null, empty, and
  whitespace-only stored text all count as absent while any
  real stored text wins byte-identically.
- **Rationale**: Implements FR-005 precedence and the
  blank/whitespace edge case in one portable expression
  valid on SQLite and Postgres; keeps Python payload code
  free of branching.
- **Alternatives considered**: Python-side `or` fallback
  (rejected — splits the rule across layers and misses
  whitespace-only unless every site strips); `COALESCE`
  without trim (rejected — violates the settled
  whitespace-counts-as-absent edge case).

## Decision: Serializers switch source, wire shape frozen

- **Decision**: `origin`/`destination` fields in
  `RouteListSerializer`, `RouteDetailSerializer`, and
  `ConnectivityResultSerializer` change `source=` from
  `from_text`/`to_text` to the annotation; field names,
  types, envelopes, hidden-field rules, and errors stay
  exactly as contracted in 003.
- **Rationale**: SC-level agreement (card/detail/evidence
  identical) falls out of sharing one annotated value;
  003 clients observe only fewer nulls, never a new shape.
- **Alternatives considered**: New `derived_origin` fields
  (rejected — shape change breaks the frozen-contract
  requirement and forces every consumer, including 004
  tools, to branch).

## Decision: Update performance-test bounds, add fallback tests, touch nothing else

- **Decision**: New tests cover tag-less routes (list,
  detail, connectivity), stored-text precedence, stop-less
  routes staying null, and single-stop routes; existing
  tests are not modified for behavior; the tightened
  per-view query-count bounds move to cover the two added
  subqueries; no model, migration, importer, throttle,
  pagination, or frontend changes.
- **Rationale**: SC-003 demands a green suite with zero
  behavior edits to existing tests; the count updates are
  the honest cost of the feature, recorded explicitly
  rather than loosened silently.
- **Alternatives considered**: Loosening bounds to vague
  ranges (rejected — the 003 convergence deliberately
  tightened them to actuals); N+1 Python fallback
  avoiding subqueries (rejected — unbounded per-page
  queries, worse under throttle budgets).

