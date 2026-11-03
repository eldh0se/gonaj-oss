# Tasks: Flat Paginated Journey Results

**Input**: Design documents from `/specs/014-flat-journey-results/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Included — required by the plan's Testing direction (update `test_ranked.py`, extend `test_area_search.py`, frontend `vitest` for cards/pager/filter) and the repo's failing-tests-first norm. Write each test task FIRST and confirm it FAILS before its implementation task.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Baseline proof before changing the answer shape

- [X] T001 Verify baseline green: run `apps.journey.tests.test_ranked`, `apps.journey.tests.test_area_search`, and the `JourneyPanel` vitest suite before any change

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Flat paged ranking engine that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 Failing engine tests in `backend/apps/journey/tests/test_ranked.py` (flat global `(stop_count, route_id)` order, `operator` + `network` carried per option, no `option_groups`, prose at most 1000 characters)
- [X] T003 Failing paging tests in `backend/apps/journey/tests/test_area_search.py` (page slices with `total_options`/`total_pages`, `page_size` clamp to 20, default 5, beyond-last-page empty, exact-multiple pages)
- [X] T004 Implement flattening in `backend/apps/journey/agent.py` (`_rank_pairs` returns one flat list with `operator`/`network` per option; `rank_pairs` slices the page and writes page-scoped prose of "at most 1000 characters"; drop `option_groups`; keep `destinations` capped at 5)
- [X] T005 Accept `page` (1-based, default 1) and `page_size` (default 5, max 20, clamp larger, never error) in `backend/apps/journey/views.py` and return `options`, `page`, `page_size`, `total_options`, `total_pages`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Flat ranked pages end to end (Priority: P1) 🎯 MVP

**Goal**: Area-to-area answers served as flat relevance-ranked pages through the endpoint

**Independent Test**: POST an area-to-area question for page 1 and page 2 and confirm relevance order, totals, and no overlap or omissions

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T006 [US1] Endpoint page-walk test via APIClient in `backend/apps/journey/tests/test_area_search.py` (page 1 then page 2: same `total_options`, disjoint option ids in global order, prose ≤ 1000 chars, no `option_groups`)

### Implementation for User Story 1

- [X] T007 [US1] Wire the paged answer through `backend/apps/journey/views.py` per `specs/014-flat-journey-results/contracts/answer-page.md` and validate the quickstart step-2 live page walk (page 1 vs page 2, no overlap)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Cards with pager and filter (Priority: P1)

**Goal**: Passengers browse paged options as cards, page through them, and narrow them with a text filter

**Independent Test**: Render cards, page forward then back, filter, clear, change page — order preserved per page, filter cleared on page change

### Tests for User Story 2 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T008 [P] [US2] Failing component tests in `frontend/src/components/JourneyPanel.test.jsx` (cards show route/stops/operator/evidence; pager pages forward/back with "Page X of Y · N options" and hides on one page; filter narrows by stop/service/operator and clear restores)

### Implementation for User Story 2

- [X] T009 [US2] Pass `page`/`page_size` in `frontend/src/api/journey.js` (`postJourney` accepts paging opts)
- [X] T010 [US2] Render cards with shared Prev/Next pager and client-side filter in `frontend/src/components/JourneyPanel.jsx` (per-page server fetch via shared `Pager`; filter over current page only, cleared on page change; plain empty state on no match)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Compact answer with operator preserved (Priority: P2)

**Goal**: Bounded summary prose with per-card operator info intact

**Independent Test**: Many-option answer carries short prose while every card names its operator

### Tests for User Story 3 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T011 [US3] Prose-cap and operator tests: backend prose summary names count plus top option within "at most 1000 characters" in `backend/apps/journey/tests/test_ranked.py`; card shows operator in `frontend/src/components/JourneyPanel.test.jsx`

### Implementation for User Story 3

- [X] T012 [US3] Tune the page-scoped summary wording in `backend/apps/journey/agent.py` until T011 passes (count + top option + evidence link, no enumeration)

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Contract alignment and full-suite proof

- [X] T013 Update the answer contracts in `specs/004-journey-agent/contracts/journey.md` and `specs/010-ranked-options/contracts/answer.md` for the flat paged shape, then run the full backend suite, the frontend suite, and the quickstart validation pass green

---

## Phase 7: Follow-up amendments (pager parity, overlay retain, disclaimer)

**Purpose**: Align the shipped UI with the routes/stops tabs and keep docs truthful

- [X] T014 Replace Load more accumulation with the shared Prev/Next `Pager` in `frontend/src/components/JourneyPanel.jsx` (export `Pager` from `ResultsList.jsx`; per-page server fetch; filter cleared on page change) with failing-first pager tests in `JourneyPanel.test.jsx`
- [X] T015 Keep journey results when the route overlay closes (client-side `Link to` evidence links instead of full-page `<a href>`), locked by the overlay-retain test in `frontend/src/App.test.jsx`
- [X] T016 Change the AI-output disclaimer to the exact text "Journey agent can make mistakes, Check important info" in `JourneyPanel.jsx` (answers, map-choice, and notice states) and update the disclaimer tests

---

## Phase 8: Convergence

- [X] T017 Route the Find-direct-routes result links through client-side navigation in `frontend/src/components/JourneyPanel.jsx` (replace the remaining `<a href>` with the shared `Link to` pattern) and extend the overlay-retain coverage in `frontend/src/App.test.jsx` so opening any journey-panel route link keeps the results per spec Edge Cases (route overlay) (partial)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - Needs the contract only; T008 can be authored in parallel with US1
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - Verified against US1/US2 output

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Engine before endpoint; endpoint before frontend handoff
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- T008 (frontend test file) can be authored in parallel with US1 backend tasks (different files, contract already fixed)
- Once Foundational completes, US1 and US2 implementation can proceed in parallel (backend response vs frontend rendering, contract-joined)
- T013 contract-doc edits are file-independent of code tasks once behavior is fixed

---

## Parallel Example: User Story 1

```bash
# T006 (endpoint page-walk test) is written first and fails against the unpaged shape:
Task: "Endpoint page-walk test via APIClient in backend/apps/journey/tests/test_area_search.py"

# T007 wires the already-built engine to the response and validates via the quickstart live walk
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (baseline green)
2. Complete Phase 2: Foundational (CRITICAL - flat paged engine + its tests)
3. Complete Phase 3: User Story 1 (endpoint page walk)
4. **STOP and VALIDATE**: Page through an area-to-area answer, confirm order/totals
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
   - Developer A: User Story 1 (endpoint walk)
   - Developer B: User Story 2 (cards + filter)
3. US3 verification follows US1/US2; Polish closes contracts and suites

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Data-model constraints applied verbatim: `page` 1-based default 1, `page_size` default 5 max 20 (clamp, never error), prose "at most 1000 characters", global `(stop_count, route_id)` order, `destinations` capped at 5, no `option_groups`, no server-side operator filter
