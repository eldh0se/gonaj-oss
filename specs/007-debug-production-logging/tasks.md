# Tasks: Debug and Production Logging

**Input**: Design documents from `/specs/007-debug-production-logging/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Included — the plan names backend `assertLogs`-style and frontend Vitest coverage as the verification mechanism, and the redaction guarantee (SC-004) is only provable by test.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `backend/`, `frontend/` (monorepo per plan.md structure decision)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm green baselines before changing shared logging behaviour

- [X] T001 [P] Run baseline backend Django test suite via `backend/manage.py` and record result
- [X] T002 [P] Run baseline frontend Vitest suite via `frontend/package.json` (`npm test`) and record result

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Mode-dependent logging infrastructure + redaction enforcement that all stories build on. No user-story work begins until this phase is complete.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation** (no `LOGGING` dict exists in `backend/config/settings.py` yet, so threshold/redaction tests must fail initially).

- [X] T003 [P] Add mode-threshold test in `backend/tests/test_logging.py` (new file): `DEBUG` entries emitted when `DJANGO_DEBUG=1`, suppressed when `DJANGO_DEBUG=0`, `ERROR` entries emitted in both modes, and every captured entry carries a timezone-aware, sortable timestamp (FR-004)
- [X] T004 [P] Add redaction sweep test in `backend/tests/test_logging.py`: captured output over config load, authenticated-adjacent paths, and user input contains zero secret/credential/token values
- [X] T005 Implement `LOGGING` dict in `backend/config/settings.py`: console `StreamHandler` to captured streams, threshold `DEBUG` when `DEBUG` is true else `INFO`, formatter with timezone-aware timestamp, level, logger name, message (depends on T003)
- [X] T006 Implement redaction filter in `backend/apps/core/redaction.py` (new file, `logging.Filter` subclass scrubbing the contract denylist: API keys, secret key, db password, tokens, authorization values, audio/transcript/question/answer content) and wire it into the `LOGGING` dict in `backend/config/settings.py` (depends on T004)
- [X] T007 [P] Add logging-resilience test in `backend/tests/test_logging.py`: a simulated log-handler write failure does not change request/command outcomes — failed and successful paths complete normally (FR-008)
- [X] T008 Lock the non-raising handler posture in `backend/config/settings.py` (stdlib defaults: handler errors are reported, never re-raised; no custom emit paths that can raise; no file I/O in the log path) with a code comment citing FR-008 (depends on T007)

**Checkpoint**: Foundation ready — `DJANGO_DEBUG=1` emits `DEBUG`, `DJANGO_DEBUG=0` emits `INFO` and above, redaction active in both modes, logging failures are non-fatal; user story implementation can now begin.

---

## Phase 3: User Story 1 - Diagnose a problem in a development environment (Priority: P1) 🎯 MVP

**Goal**: Debug mode emits detailed diagnostic entries tracing requests, import runs, and frontend API failures so a developer finds the failing component without temporary print statements.

**Independent Test**: quickstart.md Scenarios 1 (backend debug trace) and 5-dev (browser console line); a developer unfamiliar with the code names the failing component and operation from log lines alone (SC-001).

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation.**

- [X] T009 [P] [US1] Add debug-trace test in `backend/apps/transport/tests/test_logging.py` (new file): in debug mode a failing route lookup and a successful search emit `DEBUG` entries naming the component and operation (method + path)
- [X] T010 [P] [US1] Add import-phase test in `backend/apps/transport/tests/test_logging.py`: import run emits phase/progress entries plus an `INFO` outcome entry with snapshot label and counts
- [X] T011 [P] [US1] Add `DEV`-gating test in `frontend/src/api/debug.test.js` (new file): helper calls `console.debug` when `import.meta.env.DEV` is true and is silent when false

### Implementation for User Story 1

- [X] T012 [US1] Add `DEBUG`-level flow records to transport read views in `backend/apps/transport/api/views.py` using the existing `logging.getLogger(__name__)` precedent (full search text permitted at `DEBUG` per the level-based rule in contracts/logging.md §5/G-5; result counts; operation context; never request bodies) (depends on T009)
- [X] T013 [US1] Add phase and outcome records to the import flow in `backend/apps/transport/management/commands/import_osm_snapshot.py` (`INFO` outcome with snapshot label and counts, values truncated to 30 chars at `INFO` per contracts/logging.md G-5; phases at `DEBUG`) (depends on T010)
- [X] T014 [US1] Create `DEV`-gated debug helper in `frontend/src/api/debug.js` (new file, `import.meta.env.DEV`-gated so it is eliminated from production builds; entry shape per contracts/logging.md §7) and use it for API-failure diagnostics in `frontend/src/api/client.js` (depends on T011)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently — stop and validate with quickstart Scenarios 1 and 5-dev before continuing.

---

## Phase 4: User Story 2 - Triage a production issue from logs (Priority: P2)

**Goal**: Production mode stays quiet during normal operation but every error records a timestamped entry with operation context and traceback, so an operator can scope and locate failures.

**Independent Test**: quickstart.md Scenarios 2 (no `DEBUG` in production, `ERROR` with traceback on failure, response shape unchanged) and 3 (import outcome in both modes).

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation.**

- [X] T015 [P] [US2] Add error-boundary test in `backend/apps/transport/tests/test_logging.py`: a 5xx outcome logs `ERROR` with traceback and method + path, a 4xx outcome logs at most `WARNING` with no traceback, the response body keeps its plain-language shape, and every entry carries a timezone-aware, sortable timestamp (FR-004)
- [X] T016 [P] [US2] Add import-failure test in `backend/apps/transport/tests/test_logging.py`: aborted import logs `ERROR` naming the snapshot label and fatal cause in both modes

### Implementation for User Story 2

- [X] T017 [US2] Add error-boundary records to the exception path in `backend/apps/transport/api/errors.py`: `logger.exception` with method + path for 5xx, restrained `WARNING` without traceback for routine 4xx/throttling (depends on T015)
- [X] T018 [US2] Add failure-outcome record in `backend/apps/transport/management/commands/import_osm_snapshot.py`: `ERROR` with snapshot label and fatal cause on abort (depends on T016; same file as T013, apply after T013)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently — production traffic is quiet, failures are traceable.

---

## Phase 5: User Story 3 - Trust that logs are safe and do not leak sensitive data (Priority: P3)

**Goal**: A reviewer can confirm no secrets, credentials, tokens, or private content reach logs in either mode, preserving the no-tracking commitment.

**Independent Test**: quickstart.md Scenario 4 — secrets sweep over captured output in both modes (config load, journey ask, transcription, feedback paths) finds zero occurrences (SC-004).

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation.**

- [X] T019 [P] [US3] Add journey-path sweep test in `backend/tests/test_logging.py`: exercising journey ask and transcription emits no question/answer/transcript/audio content and no key material, only model/provider/latency/tool names per the journey precedent

### Implementation for User Story 3

- [X] T020 [US3] Audit existing log calls in `backend/apps/journey/agent.py` and `backend/apps/journey/views.py` against the never-log rules in `specs/007-debug-production-logging/contracts/logging.md` section 5; fix any call site that passes question, answer, transcript, audio, or key material (depends on T019; no change needed if the audit is clean — record the result)
- [X] T021 [US3] Audit new call sites from US1/US2 (`backend/apps/transport/api/views.py`, `backend/apps/transport/api/errors.py`, `backend/apps/transport/management/commands/import_osm_snapshot.py`) against the same redaction rules and fix any violation (depends on T012, T013, T017, T018)

**Checkpoint**: All user stories should now be independently functional; the full sweep passes in both modes.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end validation and final verification

- [X] T022 Run all quickstart.md validation Scenarios 1–5 in `specs/007-debug-production-logging/quickstart.md` and fix any deviation
- [X] T023 Run the full backend Django suite via `backend/manage.py` and the full frontend Vitest suite via `frontend/package.json` green with no regressions
- [X] T024 [P] Update operator-facing logging notes only if validation revealed behaviour the contract does not describe, in `specs/007-debug-production-logging/contracts/logging.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — T001 and T002 run in parallel immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phases 3–5)**: All depend on Foundational completion; then proceed in priority order (P1 → P2 → P3), or in parallel if staffed (US3 audit tasks T020/T021 depend on the US1/US2 call sites they review)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Starts after Foundational — no dependencies on other stories
- **User Story 2 (P2)**: Starts after Foundational — independently testable; reuses the Phase 2 `LOGGING` config, no US1 dependency
- **User Story 3 (P3)**: Starts after Foundational — sweep test (T019) is independent; audit tasks (T020/T021) review US1/US2 call sites, so they complete last

### Within Each User Story

- Tests written FIRST and observed to FAIL before implementation
- Foundational config before boundary call sites
- Core implementation before audit/integration tasks
- Story complete before moving to next priority

### Parallel Opportunities

- T001 ∥ T002 (baselines: different stacks, no shared files)
- T003 ∥ T004 ∥ T007 (all new tests in `backend/tests/test_logging.py` — same file; run together, or split into two files if parallel authors collide)
- T009 ∥ T010 ∥ T011 (different files: transport tests, transport tests, frontend test)
- T012 ∥ T013 ∥ T014 (different files: transport views, import command, frontend helper)
- T015 ∥ T016 (different test files/sections, no shared edits)
- T017 runs parallel with T018 (different files: `errors.py` vs import command)
- T019 ∥ T020-start (sweep test vs journey audit read; T020 fix, if needed, touches journey files)

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together (write first, watch FAIL):
Task: "Add debug-trace test in backend/apps/transport/tests/test_logging.py"
Task: "Add import-phase test in backend/apps/transport/tests/test_logging.py"
Task: "Add DEV-gating test in frontend/src/api/debug.test.js"

# Launch all implementation for User Story 1 together (after tests fail):
Task: "Add DEBUG-level flow records in backend/apps/transport/api/views.py"
Task: "Add phase and outcome records in backend/apps/transport/management/commands/import_osm_snapshot.py"
Task: "Create DEV-gated debug helper in frontend/src/api/debug.js and use in frontend/src/api/client.js"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002 baselines green)
2. Complete Phase 2: Foundational (T003–T008 — CRITICAL, blocks all stories)
3. Complete Phase 3: User Story 1 (T009–T014)
4. **STOP and VALIDATE**: quickstart Scenarios 1 and 5-dev; developer locates a reproduced failure from debug output alone (SC-001)
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → mode-dependent, redacted, non-fatal logging ready
2. Add US1 → debug diagnosis works → Validate (MVP!)
3. Add US2 → production triage works → Validate (Scenarios 2–3)
4. Add US3 → safety audit + sweep green → Validate (Scenario 4)
5. Each story adds value without breaking previous stories (response bodies and envelopes untouched throughout)

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (T009–T014)
   - Developer B: User Story 2 (T015–T018)
   - Developer C: User Story 3 sweep test (T019) + prep audit
3. Audits (T020–T021) land after US1/US2 call sites exist

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- New files vs plan.md structure: `backend/apps/core/redaction.py`, `backend/tests/test_logging.py`, `backend/apps/transport/tests/test_logging.py`, `frontend/src/api/debug.js`, `frontend/src/api/debug.test.js` — the first implements research Decision 3 (format-site denylist); the rest are the plan's named test/helper surfaces
- Response bodies, envelopes, and plain-language error wording are frozen — T015 explicitly guards them
- Error-spike behaviour: accepted per research.md Decision 7 (`ERROR` entries never suppressed); no task
- Commit after each task or logical group; stop at any checkpoint to validate the story independently

---

## Phase 7: Convergence

**Purpose**: Close the remaining gap found by `/speckit-converge` (2026-10-31) — the journey frontend module has no dev-mode diagnostics while the read-API module does.

- [X] T025 Wire the `DEV`-gated `debugLog` helper into `frontend/src/api/journey.js` failure paths (network and non-ok outcomes in `requestJson` and `postTranscribe`; log operation, path, and outcome only — never the question, history, context, or audio — per contracts/logging.md §5/§7) and cover it with a gating test in `frontend/src/api/journey.test.js` (new file) per FR-001, FR-009 (partial)
