# Implementation Plan: Place Groups for Same-Named Stops

**Branch**: `009-place-groups` | **Date**: 2026-10-31 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/009-place-groups/spec.md` plus the requester plan-time slice (Django + PostGIS-ready Postgres, reuse `servable_routes`/`order_routes`/`RouteStopMembership.position`; `tools.py` gains `search_places` + `find_routes_matrix`; keep `RESULT_LIMIT 100` and `MAX_BBOX_SPAN_DEGREES 0.5`; no model changes; Kaloor 2-group + opposite-direction tests).

## Summary

Search shows one identical button per stop, so choosing among same-named places is impossible. The fix adds two pure functions in `backend/apps/journey/tools.py`: `search_places` groups stops by normalized name plus 150 m haversine single-linkage clustering and returns `groups[{key,label,center,bbox,spread_m,members,route_count,routes}]`; `find_routes_matrix(from_ids,to_ids)` tests every pair with the existing `find_routes` travelling-order check and returns only viable pairs with `/routes/:id` evidence. No model, endpoint, or agent wiring in this slice; shape contracts are written endpoint-ready. See [research.md](research.md) for decisions and rationale.

## Technical Context

**Language/Version**: Python 3.13, Django 5.2, DRF 3.18 (backend only; no frontend changes).

**Primary Dependencies**: Existing 003 helpers (`servable_routes`, `order_routes`), `RouteStopMembership.position`, `Stop` name/name_ml/lat/lon. No new packages.

**Storage**: PostgreSQL 16 prod via plain `postgresql` backend (PostGIS image, extension pre-enabled); SQLite-portable Python haversine (no DB geo functions); no migrations — grouping is read-time derivation.

**Testing**: Django test framework, no model key needed; `python backend/manage.py test apps.journey apps.transport tests` (full-suite green gate). New Kaloor fixture tests: one shared name yields 2 groups; matrix drops opposite-direction pairs.

**Target Platform**: Existing single deployable (Django backend + PostgreSQL).

**Project Type**: Backend library slice inside `backend/apps/journey/` (pure functions + tests + shape contracts).

**Performance Goals**: Clustering runs over at most 100 stops in Python (bounded, single request); matrix reuses indexed pair queries from `find_routes`.

**Constraints**: Tools stay read-only; `RESULT_LIMIT 100` and `MAX_BBOX_SPAN_DEGREES 0.5` unchanged; `query`/`bbox` never combined; no times/schedules; no PII; `evidence` stays frontend `/routes/:id` addresses.

**Scale/Scope**: MVP audience. Two functions in one module, one fixture, 4–6 tests, one contract doc.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I (MVP validation first)**: PASS — grouping directly serves route/stop discovery for unfamiliar users.
- **II (Read-only public product)**: PASS — pure reads; no feedback/mutation surface.
- **III (No accounts, minimal data)**: PASS — no login/tracking; computed per request, nothing stored.
- **IV (Monorepo separation)**: PASS — backend-only; future endpoint consumes the same shapes via REST.
- **V (App-owned GTFS-inspired data + provenance)**: PASS — reads canonical tables; provenance untouched.
- **VI (Simple synchronous stack)**: PASS — no new infra, queues, or PostGIS dependency.
- **VII (Django Admin operations)**: PASS — no admin/data-model change.
- **VIII (Schedule gates)**: PASS — no times/schedules introduced.
- **IX (Meta AI integration)**: PASS — no model calls, prompts, or tool-schema changes ("no model changes").

*Post-design re-check (Phase 1 complete): PASS — data-model adds no tables, contracts add no endpoints, quickstart introduces no runtime behaviour.*

## Project Structure

### Documentation (this feature)

```text
specs/009-place-groups/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── places.md        # search_places / find_routes_matrix shapes (endpoint-ready)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── apps/
│   ├── journey/
│   │   ├── tools.py         # + search_places, find_routes_matrix (+ shared pair helper)
│   │   └── tests/
│   │       └── test_places.py  # Kaloor 2-group + matrix direction tests (new file)
```

**Structure Decision**: Tools-only slice in the existing journey-agent module (grouping logic lives next to the search it extends); new test file keeps place tests separate from the journey loop tests; no `agent.py`, `views.py`, model, or frontend changes.

## Complexity Tracking

No constitution violations. No entries.

## Implementation notes (for /speckit-tasks)

1. `tools.py`: `search_places(query=None, bbox=None)` — exactly-one-arg rule, `zoom_in`/`empty` semantics, cap 100 stops pre-grouping, normalize `(name.casefold().strip(), cluster)`, 150 m single-linkage haversine, centroid/bbox/`spread_m`, members `(name,id)` order, servable-route attach (`route_count` + first 10 by `(name, id)`). `find_routes_matrix(from_ids, to_ids)` — shared pair helper with `find_routes` (`position[from] < position[to]`; unknown ids error like today, equal-id pairs skipped), only viable pairs with `/routes/:id` evidence.
2. Tests in `backend/apps/journey/tests/test_places.py`: Kaloor fixture (7 same-named stops in two far-apart clusters → 2 groups with `spread_m`/counts), matrix drops opposite-direction pair, bbox/query guards, determinism (same data → same groups/order).
3. Non-goals, tracked as the next feature (010 candidate): model tool registration, prompt changes, `GET /api/v1/places/`, `agent.py` group wiring (spec FR-008 consumer — journey choice offered as place groups first).
