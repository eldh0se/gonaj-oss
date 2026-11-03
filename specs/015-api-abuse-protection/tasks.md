# Tasks: API Abuse Protection

**Input**: Design documents from `/specs/015-api-abuse-protection/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Included — required by the requester's technical direction ("Update throttle and journey tests for independent budgets, order, and clamp behavior") and the repo's failing-tests-first norm. Write each test task FIRST and confirm it FAILS before its implementation task.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Baseline proof before changing throttle behavior

- [X] T001 Verify baseline green: run `backend/apps/transport/tests/test_read_throttle.py`, `backend/apps/journey/tests/test_journey.py`, and `backend/apps/journey/tests/test_transcribe.py` before any change; confirm the existing trusted-proxy cases (`test_spoofed_forwarded_for_ignored_without_proxy`, `test_forwarded_for_honoured_with_trusted_proxy`) stay green

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Budget scopes and tunables that MUST exist before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 Add env-overridable budget and cap settings in `backend/config/settings.py` (`JOURNEY_THROTTLE_MINUTE` "60/min", `JOURNEY_THROTTLE_DAY` "1500/day", `TRANSCRIBE_THROTTLE_MINUTE` "20/min", `TRANSCRIBE_THROTTLE_DAY` "300/day", `JOURNEY_MAX_QUESTION_CHARS` 500, `JOURNEY_MAX_HISTORY_TURNS` 10, `JOURNEY_MAX_TURN_CHARS` 500, `JOURNEY_MAX_CONTEXT_BYTES` 8192) plus `DEFAULT_THROTTLE_RATES` entries for the four new scopes
- [ ] T003 Add `JourneyMinuteThrottle`, `JourneyDayThrottle`, `TranscribeMinuteThrottle`, `TranscribeDayThrottle` scopes with hashed-IP identity plus an explicit budget-check helper raising DRF `Throttled` in `backend/apps/transport/api/throttling.py` (no decorator-order dependence; no new dependencies)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Journey asks stay cheap per client (Priority: P1) 🎯 MVP

**Goal**: Journey endpoint throttles under its own per-IP minute/day budget, fully detached from shared reads; throttled asks get 429 + Retry-After with no model call

**Independent Test**: Flood journey asks from one client past budget and confirm 429s while a second client's asks, reads, and transcribe uploads still succeed

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T004 [US1] Failing budget tests: per-minute denial with `Retry-After`, no model call on denial, journey flood leaves reads and transcribe unaffected, in `backend/apps/transport/tests/test_read_throttle.py` and `backend/apps/journey/tests/test_journey.py`

### Implementation for User Story 1

- [X] T005 [US1] Wire the journey view in `backend/apps/journey/views.py`: shape + size validate first, then the explicit T003 budget check, then existing logic; detach `journey` from `READ_THROTTLE_CLASSES` (success payloads unchanged)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Voice uploads stay cheap per client (Priority: P2)

**Goal**: Transcribe endpoint throttles under its own tighter per-IP minute/day budget; throttled uploads get 429 + Retry-After with no transcription cost

**Independent Test**: Flood transcribe uploads from one client past budget and confirm 429s while a second client's uploads and journey asks still succeed

### Tests for User Story 2 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T006 [US2] Failing budget tests: per-minute denial with `Retry-After`, no transcription cost on denial, transcribe flood leaves journey asks unaffected, in `backend/apps/transport/tests/test_read_throttle.py` and `backend/apps/journey/tests/test_transcribe.py`

### Implementation for User Story 2

- [X] T007 [US2] Wire the transcribe view in `backend/apps/journey/views.py`: keep the existing 5MB WAV-only checks, then the explicit T003 budget check, then existing logic; detach `transcribe` from `READ_THROTTLE_CLASSES` (success payloads unchanged)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Oversized payloads fail fast (Priority: P2)

**Goal**: Over-cap question/history/context rejected with plain-language 400s before budget accounting and before any model call

**Independent Test**: POST over-long question, over-long history, and over-long context in turn and confirm each 400s with no model call and no budget consumed, even when the client is also over budget

### Tests for User Story 3 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T008 [US3] Failing caps/order tests in `backend/apps/journey/tests/test_journey.py`: question text at most 500 characters, history at most 10 turns with each turn at most 500 characters, context at most 8KB serialized; oversized + over-budget returns 400 (not 429); rejected requests leave budget counters untouched

### Implementation for User Story 3

- [X] T009 [US3] Implement caps validation in `backend/apps/journey/views.py` (pure bounds helper called before the budget check in `journey`); preserve existing page/page_size clamp behavior and keep its coverage green

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Production docs and full-suite proof

- [X] T010 Verify the production-hardening docs in `docs/deployment.md` and `.env.prod.example` match the implemented env names/defaults; adjust for any drift (section pre-written during review: DEBUG/ALLOWED_HOSTS, trusted-proxy-only, CGNAT monitor-and-tune note, Cloudflare/Caddy dumb-pipe posture)
- [X] T011 Run the full backend suite and the quickstart validation pass green (two-client flood checks, oversized-payload checks, env-override check per `specs/015-api-abuse-protection/quickstart.md), plus a failing-first defaults-fallback check in `backend/apps/transport/tests/test_read_throttle.py`: with budget/cap env vars unset and empty, budgets resolve to the compiled defaults and the service never starts unbounded

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P2)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Needs the contract only; T006 test authoring must sequence after T004 for the shared `test_read_throttle.py`
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - Verified against US1 output; T008 test authoring must sequence after T004 for the shared `test_journey.py`

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Scopes/settings before view wiring
- Caps validation before budget check in the view (enforcement order is contractual)
- Story complete before moving to next priority

### Parallel Opportunities

- T004, T006, and T008 test tasks share files (`test_read_throttle.py` in T004/T006, `test_journey.py` in T004/T008): author them sequentially per file, not in parallel
- US1/US2/US3 view wiring all touch `backend/apps/journey/views.py` — run sequentially, not in parallel
- T010 docs can run in parallel with any implementation phase

---

## Parallel Example: Docs Alongside Implementation

```bash
# T010 docs plus any single implementation task (different files, no dependencies):
Task: "Add the production-hardening section to docs/deployment.md"
Task: "Wire the journey view in backend/apps/journey/views.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Flood journey from one client; confirm 429s plus unaffected reads/transcribe from a second client
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3 (caps helper; coordinates views.py edits with A/B; test authoring sequences per shared test file)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- Data-model constraints are quoted verbatim in T008/T009 so defaults are not left to implementation-time discretion

---

## Phase 7: Convergence

- [X] T012 Add set-branch coverage for the env tunables in `backend/apps/transport/tests/test_read_throttle.py`: with budget/cap env vars set to non-default values, the helpers resolve the set values (unset/empty fallback is already covered; `override_settings` bypasses env entirely) per FR-007 (partial)
- [X] T013 Remove the unused `throttle_classes` import from `backend/apps/journey/views.py` left over from the decorator removal per T005/T007 (partial)
