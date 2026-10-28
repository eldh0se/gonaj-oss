# Data Model: Backend Admin Scaffold

**Feature**: [spec.md](spec.md) | **Date**: 2026-10-28

This feature introduces no transport-domain entities (spec FR-007).
The only data involved is the internal admin login.

## Admin Account (`auth.User`, built-in)

The superuser created via the documented command and used solely for
Django Admin access (constitution VII). No custom user model; no
public-user attributes exist.

- **Fields**: Django defaults (`username`, `password` hash,
  `is_superuser`, `is_staff`, standard timestamps). Nothing added.
- **Relationships**: None in this feature (no domain tables yet).
- **Validation**: Enforced by `createsuperuser` + Django auth —
  valid credentials grant a session; invalid credentials are denied
  with an error and no session (spec Story 2, scenarios 1–2).
- **State transitions**: Account exists (`new` out of scope — there is
  no public registration) → active admin session → logged out. No
  triage or workflow states apply; the feedback `new/reviewed/dismissed`
  enum belongs to a later feature.

## Deliberately absent

`Agency`, `Route`, `Stop`, `Trip`, `StopTime`, `ServiceCalendar`,
`Feedback`, `Source`, `ImportRun`, `OsmSnapshot` — all deferred to
their own features per constitution V/VIII. Their absence here is a
requirement, verified by review (spec SC-005).
