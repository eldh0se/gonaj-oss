# Contract: Versioned API Root

**Feature**: [spec.md](../spec.md) | **Date**: 2026-10-28

The only HTTP contract in this feature. It proves the DRF layer is
wired and versioned; transport endpoints arrive in later features.

## `GET /api/v1/`

Version discovery root. No authentication required (read-only
scaffold surface; no user data involved).

**Success response — `200 OK`**

```json
{
  "name": "gonaj",
  "version": "v1"
}
```

Field rules: `name` is the fixed service identifier; `version`
echoes the URL version prefix (`v1`).

**Unknown version — `404 Not Found`**

Requesting any unversioned or unknown prefix (e.g. `/api/v9/`)
MUST return `404`. Clients MUST NOT assume unversioned paths exist.

## Admin login (Django session, internal only)

- **Page**: `/admin/login/` renders the login form (HTML, not part of
  the versioned API).
- **Success**: valid superuser credentials → `302` to the admin
  dashboard with a session cookie.
- **Failure**: invalid credentials → `200` re-render with an error
  message; no session is created.
- This interface is for internal operators only and MUST NOT be
  presented as public signup or login (constitution III).
