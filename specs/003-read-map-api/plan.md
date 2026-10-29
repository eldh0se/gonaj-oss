# Implementation Plan: Read Map API

**Branch**: `003-read-map-api` | **Date**: 2026-10-29 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-read-map-api/spec.md`

## Summary

Public read-only transport API over the imported GCDA dataset:
paginated route and stop discovery (text search, exact
operator/network filters, bounding-box map lookup), route and stop
detail, and an order-aware direct-connectivity query — all under
`/api/v1/`, openly accessible with no auth and no tracking, hiding
source tags, provenance, and masters, answering every error in
plain language, and protected from basic abuse by per-IP rate
limiting (180/minute, 5,000/day) with plain-language 429 responses
— no captcha, accounts, or API keys. See
[research.md](research.md) for decisions and rationale.

## Technical Context

**Language/Version**: Python 3.13, Django 5.2, Django REST
Framework 3.18 (all established in 001; no new dependencies).

**Primary Dependencies**: Django ORM over the existing `transport`
models (`Stop`, `Route`, `RouteStopMembership`, `RouteMaster`,
`RouteMasterMembership`), DRF throttling, and Django's cache
framework. No GeoDjango, no new third-party packages.

**Storage**: PostgreSQL 16 via the existing plain `postgresql`
backend. No new tables and no migrations for domain data: this
feature is a read projection over the tables imported by 002.
Bounding-box lookup uses range predicates over the existing
`Stop(lat, lon)` float columns and their composite B-tree index.
Throttle counters use a Django database-cache table in the same
PostgreSQL (created by `createcachetable`, an operational table,
not a domain migration), keyed by hashed client IPs.

**Testing**: Django test framework with DRF test client
(`backend/apps/transport/tests/`). Fixtures built directly as model
rows (small hand-made route/stop/membership graphs) so order,
duplicates, quarantine, bbox-edge, oversized-area, and connectivity
direction cases are each provable without the full snapshot.

**Target Platform**: The existing single deployable application
(Django backend + PostgreSQL); consumers are the React frontend map
(a later feature) and AI tools calling the same public API.

**Project Type**: Backend web-service addition inside the monorepo
(`backend/` only). No frontend changes in this feature.

**Performance Goals**: List and detail reads over ~3,300 stops,
~930 routes, and ~46,000 memberships must stay single-query-shaped
(joins/prefetch, no per-row queries) so map browsing feels instant;
the shared envelope caps every page at 100 items.

**Constraints**: Read-only (GET only); open access with no auth and
no tracking (Principle III); basic abuse protection only — per-IP
throttling at 180 requests/minute and 5,000/day across all reads,
hashed expiring counter keys in the existing database cache,
client IP from the direct connection unless a known proxy is
configured, plain-language 429 with `Retry-After`, and no
captcha, accounts, or API keys; public responses hide `Stop.tags`,
all provenance (`import_run`, snapshot, recipe, OSM identifiers),
and master records (Principle V, kept internally); no schedule
fields anywhere (Principle VIII); connectivity is direct-only with
evidence links and no times or transfers (Principle IX); every
error in plain, non-technical language (spec FR-020).

**Scale/Scope**: GCDA dataset as imported by 002. Five reads: routes
list, route detail, stops list, stop detail, connectivity list.
No writes, no feedback, no AI endpoints in this feature.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I (MVP validation first)**: PASS — route/stop discovery and
  direct-service availability are the narrowed MVP validation
  question itself; this API is the surface that answers it.
- **II (read-only public product)**: PASS — GET-only reads; no
  public editing capability is introduced.
- **III (no accounts, minimal data)**: PASS — `AllowAny` reads, no
  login, no tracking, no personal data; nothing per-user is stored.
  Throttle counters are hashed-IP keys expiring with their window
  in the existing database cache — transient abuse control, not
  identification or profiling; raw IPs are never stored.
- **IV (monorepo separation)**: PASS — backend-only change behind
  the versioned `/api/v1/` REST boundary; frontend untouched and
  free to consume the contracts later.
- **V (app-owned data + provenance)**: PASS — serves only the owned
  PostgreSQL dataset (never OSM live); provenance stays stored on
  every row and is hidden — not discarded — in public responses.
- **VI (simple stack, deferred complexity)**: PASS — synchronous
  DRF views over ORM queries; no queues, routing engines, or
  journey planners. Connectivity is a same-route membership
  lookup, not a routing engine. Throttling uses Django's built-in
  database cache on the existing PostgreSQL — no Redis or new
  service; a dedicated cache is deferred until traffic proves it.
- **VII (Django Admin)**: PASS — Admin remains the curation
  interface; this feature adds no admin changes and no second
  management UI.
- **VIII (schedule gating)**: PASS — no timetable entities are
  read or exposed; connectivity returns no times (spec FR-018).
- **IX (Meta AI)**: PASS — no AI calls in this feature. The
  connectivity shape (direct-only, order-aware, evidence-linked,
  refusal-by-empty-list) is exactly what the future journey helper
  may cite, and it invents nothing.

Post-design re-check: no new principles engaged; all gates still
pass. No violations to justify — Complexity Tracking intentionally
empty.

## Project Structure

### Documentation (this feature)

```text
specs/003-read-map-api/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── read-map-api.md  # All five reads, envelope, errors
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── config/
│   ├── settings.py                # EXTEND: database cache + throttle rates + trusted-proxy setting
│   └── urls.py                    # EXTEND: mount transport API under api/v1/
├── apps/
│   ├── core/                      # existing (API root, unchanged)
│   └── transport/                 # existing domain app, extended
│       ├── models.py              # unchanged (no new tables)
│       ├── api/                   # NEW: public read API
│       │   ├── __init__.py
│       │   ├── serializers.py     # public views: hide tags/provenance/masters
│       │   ├── pagination.py      # shared envelope (default 20, cap 100)
│       │   ├── throttling.py      # per-IP throttles (hashed keys, trusted-proxy ident)
│       │   ├── errors.py          # plain-language exception handling (incl. 429)
│       │   ├── views.py           # routes/stops/detail/connectivity (GET only)
│       │   └── urls.py            # transport routes under api/v1/
│       └── tests/
│           ├── test_read_routes.py
│           ├── test_read_stops.py
│           ├── test_connectivity.py
│           └── test_read_throttle.py
└── tests/                         # existing cross-cutting tests (unchanged)
docs/
└── read-map-api.md                # NEW in T028 (docs/ is the existing repo convention from 001/002)
```

**Structure Decision**: The API lives inside the existing
`apps/transport/` app as an `api/` subpackage because the transport
domain owns the data being projected; `apps/core/` keeps only the
version root. URL wiring mounts the transport routes alongside the
core root under the single `/api/v1/` prefix in `config/urls.py`,
preserving the one versioned boundary from 001. No new app, no new
dependencies, no migrations.

## Complexity Tracking

> No constitution violations — nothing to justify. Table intentionally omitted.
