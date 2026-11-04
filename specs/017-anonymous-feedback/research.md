# Research: 017-anonymous-feedback

**Feature**: 017-anonymous-feedback | **Date**: 2026-11-04

No NEEDS CLARIFICATION remained after specify. Decisions below resolve the plan-time unknowns flagged in spec Assumptions.

## Decision: Public category vocabulary stored verbatim

- Decision: Store the requester's four categories (`incorrect`, `missing`, `outdated`, `other`) verbatim in `FeedbackReport.category` with model `choices`. No server-side remapping onto the constitution's curation vocabulary; curators interpret meaning at triage.
- Rationale: The spec's public contract pins these four values (FR-003/FR-008); silently translating user input would corrupt the receipt trail and break the 400-contract tests. Constitution II is satisfied structurally (structured category + status + human triage, no auto-reject, no auto-mutation).
- Alternatives considered: Enum-mapping to constitution categories at write time — rejected, lossy and contradicts the explicit contract.

## Decision: New `apps.feedback` Django app

- Decision: `FeedbackReport` lives in a new `apps/feedback/` app (models/views/urls/admin/tests), wired via `config/urls.py` include alongside journey/transport. Not folded into `apps.transport` or `apps.journey`.
- Rationale: Matches the repo's per-domain app layout; keeps curation data, its admin surface, and its throttle scopes isolated from the read API and the journey agent.
- Alternatives considered: Extending `apps.transport` — rejected, mixes write-model curation data with the read-only transit dataset the MVP protects.

## Decision: Throttle scopes `feedback_min` / `feedback_day`

- Decision: New scopes reusing `_HashedThrottle` + `check_budgets` + the plain 429/Retry-After handler (015 machinery). Defaults `20/min`, `100/day` via `FEEDBACK_THROTTLE_MINUTE` / `FEEDBACK_THROTTLE_DAY` env rates; documented in `.env.prod.example`.
- Rationale: Write endpoint needs tighter day budget than journey reads but room for genuine bursts; validation runs before the budget check so garbage never burns budget (015 FR-004/FR-005 ordering).
- Alternatives considered: Sharing journey budgets — rejected, couples unrelated abuse surfaces; decorator path — rejected, explicit `check_budgets` keeps validation-first ordering.

## Decision: Receipt reference generation

- Decision: Server-side `secrets.choice` over `A–Z0–9`, prefixed `FB-`, 8 chars, unique DB constraint, bounded retry (5 attempts) on collision → 500 only on genuine exhaustion (practically impossible).
- Rationale: Unpredictable (not sequential), receipt-only (never accepted from clients — supplied reference is a 400 per FR-008).
- Alternatives considered: UUID suffix — rejected, spec fixes the `FB-XXXXXXXX` shape.

## Decision: Journey ends embedded in message text

- Decision: Client sends optional `journey: {from_name, to_name, question}`; server prepends a structured header line (`Journey: {from} → {to} | Asked: {question}`) to the stored message. The 1–2000 validation applies to the user message; the header is small, fixed-shape, server-composed.
- Rationale: Honors "structured text in message; no journey schema change" literally — no new columns, no journey-app touch, curator sees context inline.
- Alternatives considered: Separate `journey_from`/`journey_to` columns — rejected, contradicts the explicit no-schema-change instruction.

## Decision: One shared frontend dialog, host in MapPage

- Decision: New `ReportDialog.jsx` (chips + category + message + states) mounted once in `MapPage`; four entry points (`header`, `RouteOverlay`, stop card, journey answer) call `onReportIssue(context)` with `{route?, stop?, journey?}`. Chips reuse `listRoutes`/`listStops`; submit via new `api/feedback.js`; submit button disabled while pending; draft state preserved on error for retry.
- Rationale: Single dialog satisfies "one dialog, no new page, map state preserved" with zero router changes; MapPage already owns overlay/stop-card state and passes handlers down.
- Alternatives considered: Per-entry dialogs — rejected, quadruples the state machine the spec explicitly unifies.
