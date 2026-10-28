# Quickstart: Backend Admin Scaffold

**Feature**: [spec.md](spec.md) | **Date**: 2026-10-28

Validates the feature end to end on a clean machine. Proves spec
Stories 1–3 and the [API contract](contracts/api-root.md). (Story 4,
PR checks, is validated by opening a pull request and observing the
check results there.)

## Prerequisites

- A Unix-like machine with the container runtime used by
  `compose.yml`, and Python per [research.md](research.md).
- A fresh clone of the repository (no prior setup).

## Steps and expected outcomes

1. **Install backend dependencies** per the setup docs.
   Expected: installation completes with no errors (FR-005,
   Story 1 scenario 1).
2. **Start the database** via the repo's container definition.
   Expected: a reachable PostgreSQL with the PostGIS extension
   available (research Decision 3).
3. **Apply migrations.** Expected: all apply cleanly; re-running is
   a safe no-op (Story 1 scenario 2; edge case).
4. **Create a superuser** via the documented command.
   Expected: account created and usable (Story 1 scenario 3).
5. **Start the development server** on the documented address.
   Expected: server serves requests (Story 1 scenario 4).
6. **Log into `/admin/login/`** with the superuser credentials.
   Expected: dashboard loads (Story 2 scenario 1); wrong credentials
   are denied with an error and no session (scenario 2).
7. **Request `GET /api/v1/`.** Expected: `200` with the discovery
   payload from the [contract](contracts/api-root.md); requesting
   `/api/v9/` returns `404` (Story 3).

## Failure drills (edge cases)

- Stop the database and start the server: expect a clear,
  actionable connection error naming the missing setting.
- Unset a required environment setting and run migrations: expect a
  fast failure naming that setting.

## Done when

All seven steps succeed following only the written docs, both
failure drills produce the specified errors, and review confirms no
transport-domain code exists (spec SC-005).
