# Quickstart: 017-anonymous-feedback

**Feature**: 017-anonymous-feedback | **Date**: 2026-11-04

## Prerequisites

- Backend migrated (`./manage.py migrate`); admin reachable; `npm test` (frontend) green on main.

## Validate

1. **Contextual report**: open a route overlay → Report issue → chip prefilled → pick `incorrect` → submit → receipt shows `FB-XXXXXXXX`; map unchanged behind the dialog.
2. **General report**: header Report issue → no chips and no search box → submit → receipt.
3. **Curator loop**: file one report per category → Django Admin lists each with reference/category/message/links/status → move one to reviewed, one to dismissed.
4. **Failures**: empty message, 2001-char message, fabricated `route_id` (expect 400 `invalid-reference`, no 500), body with `status` (expect 400), double-tap submit (one record), forced throttle (expect 429 + Retry-After + retry path).
5. **Journey context**: from a journey answer → Report issue → ends attached → submit → admin shows the `Journey: A → B | Asked: …` header in the message.

## Full suite

- `cd backend && ./manage.py test apps.feedback` (or the repo's suite entry) plus `cd frontend && npm test`.
