# Tasks: 017-anonymous-feedback

**Input**: Design documents from `/specs/017-anonymous-feedback/` (spec.md, plan.md, research.md, data-model.md, contracts/feedback.md, quickstart.md)

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Included — every story carries an Independent Test in the spec; test tasks are written FIRST and MUST FAIL before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `backend/`, `frontend/` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify green baselines before new code

- [X] T001 Run backend baseline suite green on main and record result (`cd backend && ./manage.py test` or the repo's suite entry) — 226 OK via SQLite shim (Postgres blocked in sandbox; CI runs Postgres)
- [X] T002 [P] Run frontend baseline suite green on main and record result (`cd frontend && npm test`) — 89 passed

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared model, throttle budgets, and app skeleton every story builds on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 [P] Create `apps.feedback` Django app skeleton in `backend/apps/feedback/__init__.py` and `backend/apps/feedback/apps.py`, and register `apps.feedback` in `INSTALLED_APPS` in `backend/config/settings.py` (without this, migrations, admin, and URL wiring all fail)
- [X] T004 [P] Create `FeedbackReport` model + migration in `backend/apps/feedback/models.py` (quote verbatim: `reference` `CharField(max_length=11, unique=True)` `FB-XXXXXXXX`; `category` `CharField(max_length=16, choices=[incorrect, missing, outdated, other])`; `message` `TextField`; `route`/`stop` `FK(..., SET_NULL, null=True, blank=True)`; `status` `CharField(max_length=16, choices=[new, reviewed, dismissed], default=new)`; auto `created_at`/`updated_at`; composite index `(status, created_at)`) — migration 0001 verified
- [X] T005 [P] Add `FeedbackMinuteThrottle`/`FeedbackDayThrottle` (`feedback_min`/`feedback_day`) in `backend/apps/transport/api/throttling.py`, rates in `backend/config/settings.py` (`FEEDBACK_THROTTLE_MINUTE` default `20/min`, `FEEDBACK_THROTTLE_DAY` default `100/day`), and document both vars in `.env.prod.example`

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Report about what I'm looking at (Priority: P1) 🎯 MVP

**Goal**: Report dialog opens from route overlay, stop card, and journey answer with context prefilled as chips; valid submit creates exactly one record and shows the receipt; map untouched

**Independent Test**: Open each of the three contextual entries, confirm the right chip, submit, confirm receipt + single record + unchanged map (contracts C1, C3)

### Tests for User Story 1 (write FIRST, FAIL before implementation)

- [X] T006 [P] [US1] Backend contract test in `backend/apps/feedback/tests/test_contract.py`: 201 + `{reference, receipt}` on valid contextual submit; chip-linked route/stop stored; journey header embedded in message
- [X] T007 [P] [US1] Frontend test in `frontend/src/components/ReportDialog.test.jsx` (new): dialog opens from a route-overlay entry with the route chip prefilled and map props untouched

### Implementation for User Story 1

- [X] T008 [US1] Implement `POST /feedback/` view in `backend/apps/feedback/views.py`: shape/size/reference validation BEFORE `check_budgets` (unknown ids → 400 `invalid-reference` never 500; supplied reference/status/timestamps → 400; user message stripped 1–2000, header excluded); server-composed journey header; `secrets`-based `FB-XXXXXXXX` with bounded collision retry; 201 `{reference, receipt}`; wire `backend/apps/feedback/urls.py` + `backend/config/urls.py` include
- [X] T009 [US1] Implement `postFeedback` in `frontend/src/api/feedback.js` (new)
- [X] T010 [US1] Implement shared dialog + entries in `frontend/src/components/ReportDialog.jsx` (new; chips, category, message, pending-guard, receipt view per plan Frontend Design Adherence), host in `frontend/src/App.jsx` (header entry + stop-card entry + dialog mount), entries in `frontend/src/components/RouteOverlay.jsx` and `frontend/src/components/JourneyPanel.jsx` (depends on T009)

**Checkpoint**: US1 fully functional and independently testable — contextual reporting end-to-end (MVP)

---

## Phase 4: User Story 2 - General report with no context (Priority: P1)

**Goal**: Header entry opens the same dialog chipless; chips attachable/removable via existing search; general submit works

**Independent Test**: Header entry with empty context → attach via search, remove, submit general report; all receipts (contracts C3)

### Tests for User Story 2 (write FIRST, FAIL before implementation)

- [X] T011 [P] [US2] Frontend test in `frontend/src/components/ReportDialog.test.jsx`: chipless open with no search box, general submit returns receipt

### Implementation for User Story 2

- [X] T012 [US2] Chipless open in `frontend/src/components/ReportDialog.jsx` with no in-dialog search; chips come prefilled from entry context only and are removable (depends on US1 endpoint T008; no backend change)

**Checkpoint**: US1 AND US2 both work independently

---

## Phase 5: User Story 3 - Curator triages reports (Priority: P2)

**Goal**: Reports appear in the existing internal review interface with context; status moves new → reviewed|dismissed plus re-triage

**Independent Test**: File one report per category, confirm listing with reference/category/message/links/status/timestamps, resolve and re-triage (contracts C1 data, spec US3)

### Tests for User Story 3 (write FIRST, FAIL before implementation)

- [X] T013 [P] [US3] Backend test in `backend/apps/feedback/tests/test_admin.py` (new): admin lists a report with all fields; status transitions new → reviewed, reviewed → dismissed, dismissed → reviewed persist

### Implementation for User Story 3

- [X] T014 [US3] Register `FeedbackReportAdmin` in `backend/apps/feedback/admin.py`: `list_display` (reference, category, route, stop, status, created_at), `list_filter` (status, category), `search_fields` (reference, message), all fields readonly except `status`

**Checkpoint**: US1–US3 independently functional

---

## Phase 6: User Story 4 - Failures fail plainly (Priority: P2)

**Goal**: Empty/over-long/stale-ref/throttled/duplicate submissions each get plain-language handling; single-record guarantee; retry path

**Independent Test**: Drive each failure (spec US4 AC1–AC5); confirm messages, no duplicates, retry works (contracts C1)

### Tests for User Story 4 (write FIRST, FAIL before implementation)

- [X] T015 [P] [US4] Backend edge tests in `backend/apps/feedback/tests/test_validation.py` (new): non-object body, bad category, empty/whitespace/2001-char message, non-integer ids, unknown ids → 400 `invalid-reference`, supplied reference/status/timestamps → 400, double submit → one record
- [X] T016 [P] [US4] Backend throttle test in `backend/apps/feedback/tests/test_throttle.py` (new): over-budget POST → 429 with `Retry-After`, rejected requests never consume budget
- [X] T017 [P] [US4] Frontend tests in `frontend/src/components/ReportDialog.test.jsx`: inline validation errors, 400/429/error rendering with draft preserved, retry succeeds, double-tap creates one request, plus focus-trap (focus moves into dialog on open and returns to the invoking entry on close), Esc-close, and no backdrop dismiss while pending

### Implementation for User Story 4

- [X] T018 [US4] Implement dialog error/loading/retry/pending-guard states in `frontend/src/components/ReportDialog.jsx` (backend validation/throttle already covered by T008/T005 wiring; adjust only if T015–T016 demand it)

**Checkpoint**: All user stories independently functional

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Full validation, no regressions

- [X] T019 Run `quickstart.md` validation scenarios 1–5 end-to-end (contextual, general, curator, failures, journey context)
- [X] T020 [P] Full backend suite (`cd backend && ./manage.py test apps.feedback` at minimum) and frontend suite (`cd frontend && npm test`) green with no desktop visual regression (dialog uses existing tokens only)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational completion; US2 and US4 build on the US1 endpoint/view — run sequentially in priority order (P1 → P2)
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US1 (P1)**: After Foundational - no other story dependencies (MVP)
- **US2 (P1)**: After Foundational + US1 endpoint (T008) - dialog extension only, no backend change
- **US3 (P2)**: After Foundational (model T004) - independent of US1/US2
- **US4 (P2)**: After Foundational; backend edge behavior verified against the US1 view, frontend states in the US1/US2 dialog

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Backend: model (Foundational) → view → urls wiring → admin
- Frontend: `api/feedback.js` before `ReportDialog.jsx` entries
- Story complete before moving to next priority

### Parallel Opportunities

- T001 ∥ T002 (backend vs frontend baselines)
- T003 ∥ T004 ∥ T005 (skeleton vs model vs throttling — different files)
- T006 ∥ T007 (backend vs frontend contract tests)
- T015 ∥ T016 ∥ T017 (backend validation vs backend throttle vs frontend error-state tests)
- T020 backend and frontend suite runs together after all code lands

---

## Parallel Example: User Story 1

```bash
# Launch US1 tests together (different suites, no dependencies):
Task: "Backend contract test in backend/apps/feedback/tests/test_contract.py"
Task: "Frontend dialog test in frontend/src/components/ReportDialog.test.jsx"
```

## Parallel Example: User Story 4

```bash
# Launch US4 tests together (three suites, no dependencies):
Task: "Backend edge tests in backend/apps/feedback/tests/test_validation.py"
Task: "Backend throttle test in backend/apps/feedback/tests/test_throttle.py"
Task: "Frontend error-state tests in frontend/src/components/ReportDialog.test.jsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002 baselines green)
2. Complete Phase 2: Foundational (T003–T005 — skeleton, model+migration, throttle+settings)
3. Complete Phase 3: User Story 1 (T006–T010)
4. **STOP and VALIDATE**: Test US1 independently per quickstart scenario 1
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. Add US1 → test independently → Deploy/Demo (MVP!)
3. Add US2 → test independently → Deploy/Demo (general reporting, no backend change)
4. Add US3 → test independently → Deploy/Demo (curator loop closed)
5. Add US4 → test independently → Deploy/Demo (hardened rejections)
6. Polish (T019–T020) → final gate

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: US1 backend (T006, T008 + urls)
   - Developer B: US1 frontend (T007, T009–T010)
   - Developer C: US3 (T013–T014, model-only dependency)
3. US2 follows US1; US4 follows the dialog; merge in story order

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story independently completable and testable
- Tests fail before implementation (spec Independent Tests + acceptance scenarios demand it)
- Same-file chains run sequentially (`ReportDialog.jsx`, `throttling.py`/`settings.py` only where noted)
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same-file parallel edits, cross-story dependencies that break independence
- Total: 20 tasks (T001–T020); per story: Setup 2, Foundational 3, US1 5, US2 2, US3 2, US4 4, Polish 2

---

## Phase 8: Convergence

**Purpose**: Close the two LOW gaps found by `/speckit-converge` (no constitution violations; behavior already approved)

- [X] T021 Align the in-dialog-search wording with the approved no-search direction in `specs/017-anonymous-feedback/spec.md` (FR-002, US2/AC2, ReportChip entity) and `specs/017-anonymous-feedback/contracts/feedback.md` (C3 chip-search bullet) per FR-002 (contradicts)
- [X] T022 [P] [US1] Add a `ReportDialog` test in `frontend/src/components/ReportDialog.test.jsx` that removes a prefilled route chip via its × button, submits, and asserts the POST carries no `route_id`/`stop_id` per US1/AC4 (partial)
