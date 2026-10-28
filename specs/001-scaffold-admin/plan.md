# Implementation Plan: Backend Admin Scaffold

**Branch**: `001-scaffold-admin` | **Date**: 2026-10-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-scaffold-admin/spec.md`

## Summary

Stand up the runnable backend foundation of the Gonaj monorepo: a Django
+ Django REST Framework project in `backend/` backed by PostgreSQL, with
working Django Admin login, a versioned `/api/v1/` root, a documented
fresh-clone flow (install, migrate, createsuperuser, run), a React
placeholder in `frontend/`, and CI checks on every pull request. No
transport-domain logic. See [research.md](research.md) for stack
decisions and rationale.

## Technical Context

**Language/Version**: Python 3.12+, Django 5.2 LTS line (pin exact
patch versions at implementation time).

**Primary Dependencies**: Django, djangorestframework, psycopg (v3),
plus dev tooling (test runner from Django itself, lint). Exact pins
recorded at implementation.

**Storage**: PostgreSQL 16 for development, provided via a container
definition shipped in the repo; PostGIS extension pre-enabled in that
container so the later spatial feature needs no database rebuild.
Django uses the plain `postgresql` backend until spatial fields land.

**Testing**: Django's built-in test framework (+ DRF `APITestCase` for
the API root). No extra test runner dependency for the scaffold.

**Target Platform**: Unix-like development machines; Linux container
for the database; CI on the repository's pull-request platform.

**Project Type**: web-service (monorepo: Django backend + React
placeholder frontend).

**Performance Goals**: None for the scaffold (no user-facing load);
success is measured by setup reproducibility and check reliability
(see spec SC-001–SC-004).

**Constraints**: No transport-domain models, endpoints, or data
(spec FR-007); no public user accounts — session auth exists for Admin
only (spec FR-008, constitution III/VII); secrets and connection
strings via environment only, never committed; fail fast with named
missing settings.

**Scale/Scope**: Single deployable app (web app + PostgreSQL);
small-team MVP; one backend project, one placeholder frontend, one CI
workflow.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I (MVP validation first)**: PASS — the scaffold is the foundation
  every validation feature builds on; it adds no product surface beyond
  what future validation needs.
- **II (read-only public product)**: PASS — no public product surface
  beyond the versioned API root; no user editing capability.
- **III (no accounts, minimal data)**: PASS — only internal admin
  session auth (explicitly allowed via VII); no analytics or tracking.
- **IV (monorepo separation)**: PASS — `backend/` and `frontend/`
  separated, communicating only via versioned REST; single deployable.
- **V (app-owned data + provenance)**: PASS — own PostgreSQL dataset;
  no OSM-live querying; no timetable entities touched.
- **VI (simple stack, deferred complexity)**: PASS — no event bus,
  queues, Kubernetes, or routing engine. CI on the repo host is
  ordinary deployment hygiene, not deferred infrastructure.
- **VII (Django Admin)**: PASS — admin enabled with superuser login.
- **VIII (schedule gating)**: PASS — no schedule-dependent features.
- **IX (Meta AI)**: PASS — no AI features in the scaffold; nothing to
  expose or label.

Post-design re-check: no new principles engaged; all gates still pass.
No violations to justify — Complexity Tracking intentionally empty.

## Project Structure

### Documentation (this feature)

```text
specs/001-scaffold-admin/
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
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   └── __init__.py          # placeholder for future domain apps
├── requirements.txt
├── requirements-dev.txt
└── tests/
    └── test_api_root.py

frontend/
├── package.json
└── src/
    └── placeholder App      # proves the frontend slot; real UI later

compose.yml                 # local PostgreSQL (+PostGIS) service
.github/
└── workflows/
    └── ci.yml              # install, migration check, tests on PR
```

**Structure Decision**: Web-application layout (Option 2) with real
paths above. Django project package named `config/`; domain apps land
in `backend/apps/` in later features. Database container defined once
at repo root `compose.yml` so both present and future services share
it. CI workflow lives under `.github/workflows/`.

## Complexity Tracking

> No constitution violations — nothing to justify. Table intentionally omitted.
