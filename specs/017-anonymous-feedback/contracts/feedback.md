# Contracts: 017-anonymous-feedback

**Feature**: 017-anonymous-feedback | **Date**: 2026-11-04

## C1 — POST /api/v1/feedback/ (FR-008)

POST-only, unauthenticated. Request shape validation runs before the throttle budget check.

Request (JSON object; all keys optional except `category`, `message`):

```json
{
  "category": "incorrect | missing | outdated | other",
  "message": "string, user-typed part strips to 1-2000 chars (server-composed journey header excluded from the limit)",
  "route_id": "integer, optional — must reference an existing Route",
  "stop_id": "integer, optional — must reference an existing Stop",
  "journey": "optional { from_name?: string, to_name?: string, question?: string }"
}
```

Success → `201`:

```json
{ "reference": "FB-XXXXXXXX", "receipt": "unverified — full receipt text in C2" }
```

Failures (plain-language `detail`, existing error envelope):
- Non-object body, bad/missing `category`, non-string or out-of-range `message`, non-integer ids, or presence of `reference`/`status`/`created_at`/`updated_at` → `400`.
- Unknown `route_id`/`stop_id` → `400` with `invalid-reference` (never 500).
- Throttled → `429` with `Retry-After` (existing handler wording).

## C2 — Receipt text (FR-009)

Dialog shows the `reference` only, plus: report received but not verified; reporting is anonymous with no tracking; save the reference for personal records — there is no lookup.

## C3 — Shared dialog (FR-001…FR-005, UI-level)

- Four entries (header, route overlay, stop card, journey answer) open the same dialog; no route change; map state untouched.
- Context prefills removable chips; empty state allowed; no in-dialog search.
- Category required (four options); message required (live 2000-char guidance, strip-checked on submit).
- Submit disabled while pending (single record guaranteed); errors render inline with draft preserved and a retry action.
- Receipt view replaces the form on 201; closing returns to the unchanged map.
- Design: centered modal on existing theme tokens (not a second route/stop dock); `.gonaj-journey` form patterns, list-button chips with × remove, `role=status`/`role=alert` messaging, focus-in-on-open with focus return and Esc close, full-width scrolling sheet on mobile; no new colors, type, radius, or motion.
