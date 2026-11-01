# Tasks: Choose on the Map

**Input**: Design documents from `/specs/011-choose-on-map/` (plan.md, spec.md, research.md, data-model.md, contracts/map-choice.md, quickstart.md)

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Included — explicitly requested (plan bbox/IDs/opt-out + candidate-coordinate tests; spec Independent Tests per story).

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm branch, docs, and baseline gates before any code change

- [X] T001 Verify branch `011-choose-on-map` and design docs exist in `specs/011-choose-on-map/` (plan.md, spec.md, research.md, data-model.md, contracts/map-choice.md, quickstart.md)
- [X] T002 [P] Record baselines by running `npm test -- --run` in `frontend/` and `python backend/manage.py test apps.journey apps.transport tests` in `backend/` (expect green before changes)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared interfaces the stories build on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 [P] Audit current composition in `frontend/src/App.jsx` and `frontend/src/components/MapView.jsx` (confirm `markers`/`selectedId`/`onSelectStop` props, tile-failure handling, `JourneyPanel` dock slot; quote constraint verbatim: "tile failure still falls back to the text list")
- [X] T004 [P] Audit candidate builders in `backend/apps/journey/agent.py` (confirm `_candidate_entry` outputs and both disambiguation builders where `lat`/`lon` will attach; quote constraint verbatim: "additive backend fields")

**Checkpoint**: Foundation ready — composition points and payload shapes confirmed, user story work can begin

---

## Phase 3: User Story 1 - Map moves to the candidates (Priority: P1) 🎯 MVP

**Goal**: Every same-name list auto-fits the map to all candidate pins with distinct highlighting.

**Independent Test**: Trigger a multi-candidate prompt; confirm the viewport fits every pin on first display with candidates visually distinct.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T005 [US1] Add candidate-coordinate assertions in `backend/apps/journey/tests/test_journey.py` (every `disambiguate` candidate carries `lat`/`lon`; quote constraint verbatim: "Every `disambiguate` response used for map help carries `lat`/`lon` per candidate")
- [X] T006 [US1] Add bbox-fit test in `frontend/src/components/JourneyPanel.test.jsx` (disambiguate with spread candidates yields `onShowCandidates` bounds containing every pin; quote constraint verbatim: "The fitted bounds always contain every candidate pin on first display")

### Implementation for User Story 1

- [X] T007 [US1] Attach `lat`/`lon` to disambiguate candidates in `backend/apps/journey/agent.py` (both enriched and partial-prompt builders; additive only, existing `id`/`name`/`detail` untouched)
- [X] T008 [US1] Add `fitBounds`/`highlightIds` props in `frontend/src/components/MapView.jsx` (`fitBounds` applied once per change; candidate amber style distinct from the selected-stop style; existing marker/selection behaviour unchanged)
- [X] T009 [US1] Wire candidate view in `frontend/src/App.jsx` (candidate-view state from `onShowCandidates`; pass `fitBounds`/`highlightIds`/`markers` to `MapView`; clear on answer, refusal, or new question)

**Checkpoint**: US1 fully functional and independently testable — auto-fit distinct pins for every same-name list

---

## Phase 4: User Story 2 - Pick a pin or answer none of these (Priority: P1)

**Goal**: Pin taps resolve via the identical 008 protocol; `none of these` resets to a fresh guided question.

**Independent Test**: Tap a pin and confirm exact-stop resolution; answer `none of these` and confirm a guided retry with no leak.

### Tests for User Story 2 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T010 [US2] Add pin-pick payload test in `frontend/src/components/JourneyPanel.test.jsx` (pin tap sends byte-identical 008 payload to the list button; quote constraint verbatim: "Pin taps send byte-identical 008 selection payloads to list-button picks")
- [X] T011 [US2] Add none-of-these test in `frontend/src/components/JourneyPanel.test.jsx` (action resets to `history: []`, `context: {}` and re-asks fresh; stale candidates never leak)

### Implementation for User Story 2

- [X] T012 [US2] Route pin taps through `choose` in `frontend/src/components/JourneyPanel.jsx` (same IDs + `slot`/`resolved`/`slots`, preserved history; no new payload shape)
- [X] T013 [US2] Implement `none of these` in `frontend/src/components/JourneyPanel.jsx` (clears context to a fresh question with rephrase help; quote constraint verbatim: "stale candidates never leak")

**Checkpoint**: US1 and US2 both work — interchangeable pin/list picks plus honest retry

---

## Phase 5: User Story 3 - Dismiss map help and continue by text (Priority: P2)

**Goal**: Per-exchange dismiss hides map help; text list alone completes the journey; auto-show returns next time.

**Independent Test**: Dismiss during a choice; confirm text-only completion with no re-prompts, then auto-show on the next list.

### Tests for User Story 3 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T014 [US3] Add dismiss test in `frontend/src/components/JourneyPanel.test.jsx` (dismiss hides map help for the exchange; quote constraint verbatim: "Decline state resets on each new journey question"; next same-name list auto-shows)

### Implementation for User Story 3

- [X] T015 [US3] Implement per-exchange dismiss in `frontend/src/components/JourneyPanel.jsx` (dismiss control setting unpersisted state; `null` view to `onShowCandidates`; never blocks text-list completion)

**Checkpoint**: All user stories independently functional — auto-show, interchangeable picks, respected decline

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Privacy gate, regressions, and invariants across all stories

- [X] T016 [P] Add geolocation opt-out test in `frontend/src/components/JourneyPanel.test.jsx` (opt-out payloads carry no coordinates; quote constraint verbatim: "Opt-out journey payloads contain no coordinates; the geolocation API is never invoked unless explicitly opted in")
- [X] T017 [P] Implement explicit geolocation opt-in defaulting to off in `frontend/src/App.jsx` (only path that may center the map on the user; coordinates never attached to journey payloads)
- [X] T018 Run frontend regression `npm test -- --run` in `frontend/` (gate: all green including new map-choice tests)
- [X] T019 Run backend regression `python backend/manage.py test apps.journey apps.transport tests` in `backend/` (gate: all green including candidate-coordinate assertions)
- [X] T020 Run `specs/011-choose-on-map/quickstart.md` validation (auto-fit, pin-tap parity, none-of-these retry, decline, opt-out silence)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - US1 (P1) then US2 (P1) in priority order; US3 (P2) after (JourneyPanel tasks share one file — do not parallelize within it; backend T007 is independent of frontend work)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational — no dependencies on other stories (MVP)
- **User Story 2 (P1)**: Can start after Foundational — pin taps reuse US1 view + 008 payloads, independently testable via T010–T011
- **User Story 3 (P2)**: Can start after Foundational — per-exchange dismiss over US1 view, independently testable via T014

### Within Each User Story

- Tests MUST be written and FAIL before implementation (T005–T006 before T007–T009; T010–T011 before T012–T013; T014 before T015)
- Backend coordinates (T007) before frontend bbox (bbox test T006 may stub coordinates; T006 does not block on T007)
- Story complete and checkpoint-validated before moving to next priority

### Parallel Opportunities

- T002 (baselines) can run alongside T001 (docs check)
- T003 + T004 (frontend vs backend audits, different areas) can run in parallel
- Backend T007 can proceed in parallel with frontend US1 work (T008–T009 touch different files)
- T016 + T017 (opt-out test vs opt-in control, test-first order respected) can overlap in preparation but T017 implements after T016 is written
- T018 + T019 (frontend vs backend regressions, different suites) can run in parallel

---

## Parallel Example: User Story 1

```bash
# Tests first (different files, parallel):
# T005: "candidate coordinate assertions in backend/apps/journey/tests/test_journey.py"
# T006: "bbox-fit test in frontend/src/components/JourneyPanel.test.jsx"

# Implementation (different files, parallel after tests):
# T007: "lat/lon in backend/apps/journey/agent.py"
# T008+T009: "MapView props + App wiring (sequential — shared composition)"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundational (T003–T004)
3. Complete Phase 3: User Story 1 (T005–T009)
4. **STOP and VALIDATE**: Every same-name list auto-fits distinct pins; coordinates present
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → composition and shapes confirmed
2. Add US1 → auto-fit distinct pins (MVP!)
3. Add US2 → interchangeable pin picks + honest retry (T010–T013)
4. Add US3 → respected decline (T014–T015)
5. Polish → privacy gate + full green (T016–T020)

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: Backend coordinates (T005, T007 in `backend/`)
   - Developer B: Frontend map view (T006, T008–T009 in `frontend/`)
3. Joint US2 (T010–T013), then US3 (T014–T015)
4. Joint Polish (T016–T020)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable via its Independent Test
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint and validate the story independently

---

## Phase 7: Convergence

**Purpose**: Close the single remaining low-severity gap found by `/speckit-converge`

- [X] T021 Reset the `fitBounds` dedupe key when the candidate view clears in `frontend/src/components/MapView.jsx` per spec FR-001 (partial)
