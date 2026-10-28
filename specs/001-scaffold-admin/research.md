# Research: Backend Admin Scaffold

**Feature**: [spec.md](spec.md) | **Date**: 2026-10-28

All unknowns below were resolved as decided defaults (the user input
pinned the stack explicitly, so no NEEDS CLARIFICATION remained).
Exact patch versions are pinned at implementation time against current
releases; the lines below fix the version lines, not individual patches.

## Decision: Python 3.12+ with Django 5.2 LTS line

- **Decision**: Python 3.12 or newer; Django 5.2 LTS line.
- **Rationale**: Django 5.2 is the long-term-support release, so the
  scaffold avoids a framework upgrade during MVP life. Python 3.12 is
  the conservative floor with broad container and CI support.
- **Alternatives considered**: Django 4.2 LTS (older; shorter remaining
  support), Django latest non-LTS (forces upgrades mid-MVP).

## Decision: DRF for the versioned API, plain routers

- **Decision**: Django REST Framework serving `/api/v1/`; the version
  root returns a small discovery payload (`{name, version}`).
- **Rationale**: Constitution Principle IV/VI fixes REST + DRF; a
  versioned root from day one means the future frontend never depends
  on unversioned URLs.
- **Alternatives considered**: Plain Django views for the root (saves
  one dependency but defers the DRF wiring every later endpoint needs
  anyway).

## Decision: PostgreSQL 16 via repo-shipped container, PostGIS pre-enabled

- **Decision**: `compose.yml` at repo root defines the dev database
  (PostgreSQL 16 image carrying PostGIS); Django connects via
  environment settings using the plain `postgresql` backend.
- **Rationale**: A shipped container makes "reachable database" one
  documented command, keeping the fresh-clone flow reproducible.
  Pre-enabling the PostGIS extension now avoids rebuilding or
  re-provisioning the database when spatial fields arrive, while the
  plain backend keeps GDAL/GEOS system dependencies out of the
  scaffold.
- **Alternatives considered**: Requiring a locally installed
  PostgreSQL (more setup friction, OS-specific docs); GeoDjango from
  day one (adds native GIS system dependencies before any spatial
  feature needs them).

## Decision: psycopg v3 driver

- **Decision**: `psycopg` (v3 line) as the Postgres driver.
- **Rationale**: Current maintained driver line, binary wheels
  available, works with Django's postgresql backend.
- **Alternatives considered**: `psycopg2-binary` (older line, still
  fine, but v3 is the maintained path for new projects).

## Decision: Default `auth.User`, no custom user model

- **Decision**: Use Django's built-in `auth.User` for the admin
  superuser; no custom user model in the scaffold.
- **Rationale**: The product has no public accounts by design
  (constitution III), so the user model will only ever serve internal
  admin login. A custom model adds code with no foreseeable consumer.
- **Alternatives considered**: Custom user model from day one
  (standard advice for public-facing auth; inapplicable here since
  public auth is constitutionally out of scope).

## Decision: Django test framework, no extra runner

- **Decision**: `manage.py test` with DRF `APITestCase` for the API
  root contract; no pytest in the scaffold.
- **Rationale**: Zero extra dependencies for what the scaffold must
  prove (migrations apply, admin login, API root responds). pytest can
  be adopted later if the suite outgrows the built-in runner.
- **Alternatives considered**: pytest + pytest-django from day one
  (more power, more config for an initially tiny suite).

## Decision: React placeholder, no routing or state

- **Decision**: `frontend/` holds a minimal placeholder app proving the
  directory, toolchain, and API-call path exist; no routes, state, or
  map in this feature.
- **Rationale**: Reserves the constitution's frontend slot and proves
  monorepo separation without spending MVP effort before backend
  endpoints exist.
- **Alternatives considered**: Empty `frontend/` dir (proves nothing
  about toolchain); full map UI now (premature — no endpoints to call).

## Decision: CI on the repo host, three jobs

- **Decision**: One workflow on pull requests: install → migration
  check (`makemigrations --check`) → test suite; results visible on
  the PR and required before merge.
- **Rationale**: Covers the scaffold's three failure modes (broken
  deps, broken/missing migrations, broken code) with no extra services.
- **Alternatives considered**: Lint-only or test-only workflows (leave
  known failure modes uncovered); multi-service matrix (unneeded for a
  single app).

## Decision: Plain `requirements.txt` files

- **Decision**: `requirements.txt` (runtime) +
  `requirements-dev.txt` (local/CI extras).
- **Rationale**: Simplest mechanism every Python developer and CI
  image understands; no build-backend ceremony for a deployable app.
- **Alternatives considered**: `pyproject.toml`-only with pip
  (equivalent power, less universally familiar for Django deploy
  targets); Poetry/uv workspaces (locker tooling before any
  dependency pain exists).
