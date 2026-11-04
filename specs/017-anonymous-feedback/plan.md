# Implementation Plan: 017-anonymous-feedback

**Branch**: `017-anonymous-feedback` | **Date**: 2026-11-04 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/017-anonymous-feedback/spec.md` — anonymous passenger feedback for the single-page transport map (4 stories, FR-001…FR-010).

## Summary

One shared report dialog reachable from four MapPage entry points (route overlay, stop card, journey answer, header) with searchable removable context chips; a new `apps.feedback` backend app persisting `FeedbackReport` (unique `FB-XXXXXXXX` receipt references, category, message with embedded journey ends, optional SET_NULL route/stop links, new/reviewed/dismissed status) behind a throttled public `POST /api/v1/feedback/`; review through Django Admin only; receipt shows the reference plus anonymous/unverified/no-lookup text. No accounts, no tracking, no canonical writes.

## Technical Context

**Language/Version**: Python 3.13 + Django 5.2 / DRF (backend); JavaScript (JSX) + React 18.3.1 (frontend, constitution v1.4.0 JSX precedent)

**Primary Dependencies**: Django + DRF, PostgreSQL + PostGIS (prod) / SQLite (dev shim); React 18, react-router-dom 6, Leaflet 1.9.4 (map untouched), vitest 2 + Testing Library + jsdom

**Storage**: PostgreSQL: new `feedback_feedbackreport` table (reference unique, category, message, route FK SET_NULL, stop FK SET_NULL, status, timestamps). Throttle counters reuse the existing `transport_throttle_cache` DB table — no new table.

**Testing**: Backend: Django tests under `backend/apps/feedback/tests/` (contract, validation, throttle, admin); run per repo gate. Frontend: vitest (`cd frontend && npm test`); new `ReportDialog` suite + entry-point wiring tests in `App`/`JourneyPanel`/`RouteOverlay` suites.

**Target Platform**: Responsive web frontend + Django API; no native app

**Project Type**: Web application — new backend app `backend/apps/feedback/` + frontend dialog (`frontend/src/components/ReportDialog.jsx`, `frontend/src/api/feedback.js`)

**Performance Goals**: Single-row INSERT per valid report; reference generation bounded-retry on collision; chip search reuses existing paged endpoints (no new search load); no new fetch on dialog open.

**Constraints**:
- POST-only, unauthenticated, AllowAny — same shape as journey endpoints; shape/size/reference validation runs BEFORE the budget check so rejects never consume budget (015 precedent).
- New throttle scopes `feedback_min`/`feedback_day` (`FEEDBACK_THROTTLE_MINUTE` default `20/min`, `FEEDBACK_THROTTLE_DAY` default `100/day`), reusing `_HashedThrottle` + `check_budgets` + the plain 429 wording/Retry-After handler.
- Public contract frozen per spec: 201 + `{reference, receipt}` on success; 400 `invalid-reference` for unknown ids (never 500); 400 when reference/status/timestamps supplied; 400 for category/message violations; journey ends embedded as structured text header in stored message, no journey-schema change.
- Frontend: one dialog component, no new route; map state untouched; chips reuse `listRoutes`/`listStops`; duplicate-submit blocked while pending; draft preserved across retry.
- Review via Django Admin only (`FeedbackReportAdmin`: list/filter/search, status editable, everything else readonly). No public listing, no admin REST.
- Constitution II category note: public contract uses the requester's four categories verbatim; no silent remapping (see research).

## Frontend Design Adherence

The new dialog and chips MUST look native to the existing single-page map — no new palette, type, radius, or motion language:

- **Surface**: dialog is a centered modal using existing tokens (`--gonaj-surface`, `--gonaj-line`, `--gonaj-radius`, `--gonaj-backdrop` scrim); NOT a second `.gonaj-overlay` dock — the overlay pattern stays reserved for route/stop detail.
- **Form**: labels, inputs, textarea, and category select reuse the `.gonaj-journey` form patterns (14px inputs, 10px radius, green `focus-visible` outline); primary submit is the existing green button pattern, secondary/close the existing bordered button pattern.
- **Chips**: context chips reuse the list-button pattern (surface fill, line border, radius) with an inline × remove affordance in the existing stop-clear style; chip rows wrap like `.gonaj-stop-picker` content.
- **Messaging**: loading/validation/error states use the existing `role=status` / `role=alert` patterns and plain-language tone; receipt reference renders prominently but in-theme (ink, semibold — no new badge color; the amber unverified pill stays reserved for AI answers).
- **Motion/focus**: no entrance animation beyond what the theme already uses; honor `prefers-reduced-motion`; focus moves into the dialog on open and returns to the invoking entry on close; Esc closes (draft kept only for retry-after-error, otherwise discarded).
- **Mobile**: dialog fits within the ≤48rem layout (full-width sheet with internal scroll, same as the capped overlay pattern); backdrop tap does NOT dismiss mid-pending-submit.

**Scale/Scope**: 4 stories; backend ~6 files (models/views/urls/admin/tests/migration) + `config/urls.py` include + settings rates; frontend ~2 new files + 4 entry-point edits + CSS; ~6 test suites.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- I. MVP Validation: PASS — corrective feedback on routes/stops/journeys directly serves curation of the MVP discovery question.
- II. Read-Only + Feedback: PASS with note — no canonical mutation; reports carry category + status as structured data. Public category vocabulary is the requester's four values, stored verbatim; curator triage maps meaning at review. No auto-reject, no auto-mutation.
- III. No accounts/tracking: PASS — anonymous, no login; only the existing hashed-IP throttle identity (no raw IPs stored, 015 precedent).
- IV. Monorepo separation: PASS — new `apps.feedback` backend app + frontend dialog, communicating only via versioned REST.
- V. Provenance: PASS — FeedbackReport is new curation data with its own reference/timestamps; route/stop links are FK references, never OSM writes; provenance untouched.
- VI. Simple stack: PASS — plain Django view + DB cache reuse; no new services.
- VII. Admin: PASS — review exclusively through Django Admin, no separate admin frontend.
- VIII. Schedule gating: PASS — no schedule content, no WRONG_SCHEDULE category offered (unavailable data), non-schedule feedback allowed.
- IX. Meta AI: N/A — no AI involvement (explicit non-goal: no auto-moderation, no AI categorization).
- Stack (JSX): PASS — new dialog follows scaffold JSX precedent.

Post-design re-check: no new gates tripped — research/data-model/contracts/quickstart introduce no accounts, tracking, AI, schedule content, or extra services.

## Project Structure

### Documentation (this feature)

```text
specs/017-anonymous-feedback/
├── spec.md              # Feature specification
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── feedback.md      # Phase 1 output (REST contract + dialog contract)
└── tasks.md             # Phase 2 output (/speckit-tasks command — NOT created here)
```

### Source Code (repository root)

```text
backend/
├── apps/feedback/
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py        # FeedbackReport
│   ├── views.py         # POST /feedback/ (validate → budget → create → 201)
│   ├── urls.py          # path("feedback/", ...)
│   ├── admin.py         # FeedbackReportAdmin
│   ├── migrations/
│   └── tests/
│       ├── test_contract.py
│       ├── test_validation.py
│       └── test_throttle.py
├── config/
│   ├── urls.py          # include("apps.feedback.urls")
│   └── settings.py      # feedback_min/feedback_day rates
└── .env.prod.example    # FEEDBACK_THROTTLE_MINUTE/DAY (docs; defaults ship in settings)

frontend/
├── src/
│   ├── api/feedback.js          # postFeedback (new)
│   ├── components/ReportDialog.jsx  # shared dialog (new)
│   ├── components/ReportDialog.test.jsx
│   ├── App.jsx                  # header entry + dialog host + stop-card entry
│   ├── components/RouteOverlay.jsx   # Report issue entry
│   └── components/JourneyPanel.jsx   # answer-level Report issue entry
└── tests (colocated *.test.jsx per component)
```

**Structure Decision**: New `apps.feedback` Django app (mirrors the `apps.journey` per-domain layout) plus a colocated frontend dialog; REST is the only boundary crossing.

## Complexity Tracking

> No constitution violations — table intentionally empty. The Principle II category-vocabulary note is a documented requester decision, not a violation: reports still carry structured category + status with human triage.
