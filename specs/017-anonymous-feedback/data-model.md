# Data Model: 017-anonymous-feedback

**Feature**: 017-anonymous-feedback | **Date**: 2026-11-04

## FeedbackReport (FR-006, FR-008)

New table `feedback_feedbackreport` in the `feedback` app. Write-once from the public endpoint; status transitions only via Django Admin.

- `reference`: `CharField(max_length=11, unique=True)` — `FB-XXXXXXXX` (8 uppercase alphanumerics), server-generated, receipt-only. Never accepted from clients (supplied value → 400).
- Glossary: *reference* is the `FB-XXXXXXXX` identifier alone; *receipt* is the reference plus the unverified/anonymous/no-lookup text shown to the passenger.
- `category`: `CharField(max_length=16, choices=[incorrect, missing, outdated, other])` — stored verbatim from the request; anything else → 400.
- `message`: `TextField` — server-composed as `[Journey: {from} → {to} | Asked: {question}\n\n]` header (only parts provided, only when journey context sent) + user message stripped, 1–2000 chars (user part; header excluded from the limit).
- `route`: `FK(Route, SET_NULL, null=True, blank=True)` — validated by id at submit (unknown id → 400 `invalid-reference`); cleared automatically if the route is later deleted.
- `stop`: `FK(Stop, SET_NULL, null=True, blank=True)` — same semantics as route.
- `status`: `CharField(max_length=16, choices=[new, reviewed, dismissed], default=new)` — public input rejected (supplied value → 400); Admin-editable only.
- `created_at` / `updated_at`: auto timestamps — public input rejected (supplied values → 400).
- Indexes: unique `reference`, plus a composite `(status, created_at)` index for the curator queue (`list_filter` + newest-first ordering). Category-only filtering rides on table scans acceptable at feedback volumes.

Validation rules (all before budget check, all 400 with plain language):
- Body must be a JSON object; `category` must be one of the four values; `message` must be a string stripping to 1–2000 chars.
- `route_id`/`stop_id`, when present, must be integers referencing existing rows (unknown → 400 `invalid-reference`, never 500); absent/null means no link.
- Presence of `reference`, `status`, `created_at`, or `updated_at` keys → 400.

State transitions: `new` → `reviewed` | `dismissed`, plus `reviewed` ↔ `dismissed` for re-triage (Admin only; no transitions exposed publicly). The removal of re-triage was never intended — curators must be able to correct a misfiled resolution.

## ReportChip (FR-002, transient UI only)

- Source: entry-point context (`{route?, stop?, journey?}`) plus user search via existing `listRoutes`/`listStops`.
- Shape: `{kind: route|stop|journey, id?, name, detail?}`; journey chips render ends text and serialize into the `journey` submit field.
- Transitions: attach (prefill or search-pick) → remove (user) → submit (serialized) or discard (dialog closed). Never persisted.
