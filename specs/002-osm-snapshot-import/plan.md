# Implementation Plan: OSM Snapshot Import

**Branch**: `002-osm-snapshot-import` | **Date**: 2026-10-29 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-osm-snapshot-import/spec.md`

## Summary

Offline import of the GCDA Overpass snapshot into the application's own
PostgreSQL dataset via an `import_osm_snapshot` management command:
parse the retained snapshot directory (no network I/O), upsert stops,
routes, route masters, and their memberships idempotently on
(`osm_type`, `osm_id`) inside a single transaction, record every
deviation as a severity-coded anomaly without silent repair, and emit a
machine-readable JSON report plus a console summary. See
[research.md](research.md) for stack decisions and rationale.

## Technical Context

**Language/Version**: Python 3.13, Django 5.2 (established in 001).

**Primary Dependencies**: Standard library `json` plus the Django ORM.
No new third-party dependencies.

**Storage**: PostgreSQL 16; eight new tables (see
[data-model.md](data-model.md)). Composite B-tree index on
`Stop(lat, lon)`. Plain `postgresql` backend — no GeoDjango/PostGIS
use until the spatial feature needs it (consistent with 001).

**Testing**: Django test framework. Sample snapshot files are copied
into the transport app's test fixtures at implement time; the full
`data/osm/gcda/` snapshot stays out of git and is exercised via the
manual quickstart path.

**Target Platform**: Unix-like development machines; CI on the
repository's pull-request platform.

**Project Type**: Backend data pipeline (management command) inside the
monorepo's Django backend. No frontend changes.

**Performance Goals**: Full GCDA snapshot imports in under 30 minutes
(spec SC-005). The ~30 MB of JSON parses in memory — acceptable on a
developer machine and required for cross-file joins and order
preservation.

**Constraints**: Offline by construction (no socket use in the importer);
parse-then-write inside one database transaction (a failed run leaves
no partial dataset); snapshot files are read-only input; no silent
repair of source deviations; no geographic filtering (snapshot is
pre-scoped).

**Scale/Scope**: ~3,300 stops, ~930 routes, ~465 route masters, ~46,000
stop-events per the current snapshot. GCDA scope only; further regions
are later features with their own snapshots.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I (MVP validation first)**: PASS — the base transit dataset is the
  prerequisite for every validation question (routes, stops, services).
- **II (read-only public product)**: PASS — the import is an internal
  data-loading path; it grants no public editing capability.
- **III (no accounts, minimal data)**: PASS — no user accounts, no
  tracking; OSM data is public infrastructure geometry.
- **IV (monorepo separation)**: PASS — backend-only change; the
  versioned API and frontend are untouched.
- **V (app-owned data + provenance)**: PASS — snapshot imported into
  the owned dataset (never queried live); `OsmSnapshot` carries all
  five mandated fields; every record resolves record → run → snapshot
  → recipe.
- **VI (simple stack, deferred complexity)**: PASS — no event bus,
  queues, or routing engines. A single management-command transaction
  is the sanctioned simple path, not deferred infrastructure.
- **VII (Django Admin)**: PASS — the command is the bulk-load path
  that VI explicitly sanctions for imports (`import_osm_transit`
  pattern); Admin remains the curation/review interface, so the new
  models are registered there for anomaly review.
- **VIII (schedule gating)**: PASS — structure only; no timetable
  entities are populated.
- **IX (Meta AI)**: PASS — no AI features in this import.

VII-vs-command reconciliation: VII governs ongoing curation (Admin);
VI governs bulk data preparation (management commands). This feature
uses each for its constitutionally assigned role.

Post-design re-check: no new principles engaged; all gates still pass.
No violations to justify — Complexity Tracking intentionally empty.

## Project Structure

### Documentation (this feature)

```text
specs/002-osm-snapshot-import/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── manage.py
├── config/
├── apps/
│   ├── core/                    # existing (API root)
│   └── transport/               # NEW: transit domain + import
│       ├── models.py            # 8 entities (see data-model.md)
│       ├── admin.py             # review/curation registration
│       ├── importer/            # parsing, policy engine, reporting
│       │   ├── __init__.py
│       │   ├── parse.py         # Overpass JSON → ordered records
│       │   ├── policy.py        # verdict/anomaly rules, stable codes
│       │   └── report.py        # JSON report + console summary
│       ├── management/
│       │   └── commands/
│       │       └── import_osm_snapshot.py
│       └── tests/
│           ├── __init__.py
│           ├── test_import.py
│           └── fixtures/osm/    # sample snapshot copies (tracked)
└── tests/                       # existing cross-cutting tests
```

**Structure Decision**: Domain logic lives in a new `backend/apps/transport/`
app (per the 001 plan's `backend/apps/` convention), self-contained with
its own tests and fixtures. `backend/tests/` remains for cross-cutting
concerns. The management command is the only new entry point; no URL,
view, or frontend changes.

## Complexity Tracking

> No constitution violations — nothing to justify. Table intentionally omitted.
