# Implementation Plan: Route Endpoint Fallback

**Branch**: `006-route-endpoint-fallback` | **Date**: 2026-10-29 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/006-route-endpoint-fallback/spec.md`

## Summary

When a route's stored `from_text`/`to_text` is null or blank,
the read API serves the endpoint stop names (first/last
ordered membership) as `origin`/`destination` instead —
identically in route list, route detail, and connectivity
results. One shared queryset helper annotates the resolved
values with `Coalesce(NullIf(Trim(...)))`; the three payload
sites read the annotation; stored text always wins; response
shapes, envelopes, and errors are untouched. See
[research.md](research.md) for decisions and rationale.

## Technical Context

**Language/Version**: Python 3.13, Django 5.2 + DRF
(existing backend stack, unchanged).

**Primary Dependencies** (none new): Django ORM
`Subquery`/`OuterRef` (already used for master fields and
ordering), `Coalesce`/`NullIf`/`Trim` comparison and text
functions. No new packages, migrations, or services.

**Storage**: No schema change. The fallback is derived at
request time; nothing is written back (`from_text`/`to_text`
stay exactly as imported).

**Testing**: Existing backend suite (`backend/` Django
tests) under the project's SQLite/Postgres test setup;
new fallback tests alongside `test_read_routes.py` /
`test_connectivity.py`; performance-test query-count bounds
updated for the added subqueries.

**Target Platform**: Same deployable (web app +
PostgreSQL/PostGIS); the feature is portable SQL valid on
both SQLite and Postgres.

**Project Type**: Backend API behavior change inside the
monorepo (`backend/` only; zero frontend changes — the UI
already renders these fields).

**Performance Goals**: Two extra correlated subqueries per
route row, on indexed `route_id`; list/connectivity pages
stay within updated per-view query-count bounds. No N+1:
no per-row Python queries.

**Constraints**: 003 contract frozen — same fields, same
envelope, same hidden-field rules, same errors; stored
non-blank text always wins; stop-less routes stay null;
whitespace-only stored text counts as absent.

**Scale/Scope**: MVP audience. Three payload sites, one
helper, serializer source switch, contract-delta doc, tests.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I (MVP validation first)**: PASS — closes the reported
  card/detail disagreement, a validation-blocking confusion.
- **II (read-only public product)**: PASS — GET-only reads;
  no writes, no feedback/data-entry surface; nothing stored.
- **V (app-owned data + provenance)**: PASS — no new stored
  data, no import change, provenance untouched; derived
  values only, hidden-field rules unchanged.
- **VI (simple stack, deferred complexity)**: PASS — two ORM
  subqueries in the existing pattern; no services, queues,
  engines, or migrations.
- **III (no accounts, minimal data)**: PASS — no identity,
  no tracking, no new signals.
- **IV (monorepo separation)**: PASS — backend-only change
  behind the versioned REST boundary; frontend untouched.
- **VII (Django Admin)**: PASS — no data operations.
- **VIII (schedule gating)**: PASS — no times or schedules.
- **IX (Meta AI)**: PASS — no AI surface; evidence URLs
  keep resolving to richer details.

Post-design re-check: no new principles engaged; all gates
still pass. No violations to justify — Complexity Tracking
intentionally empty.

## Project Structure

### Documentation (this feature)

```text
specs/006-route-endpoint-fallback/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── endpoint-fallback.md  # Contract delta vs 003 (values change, shape frozen)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── apps/transport/api/
│   ├── views.py         # EXTEND: shared endpoint-annotation helper; three payload sites read it
│   ├── serializers.py   # EXTEND: origin/destination source switches to the annotation
│   └── tests/
│       ├── test_read_routes.py      # EXTEND: fallback cases (list + detail)
│       └── test_connectivity.py     # EXTEND: fallback case
└── (no models, migrations, importers, throttling, pagination, or frontend changes)
```

**Structure Decision**: The annotation helper lives next to
`routes_with_master_fields` in `views.py`, following that
exact pattern, so all three views share one precedence rule
instead of three copies. Serializers switch `source=` to the
annotated field, which keeps the wire shape byte-identical.

## Complexity Tracking

> No constitution violations — nothing to justify. Table intentionally omitted.
