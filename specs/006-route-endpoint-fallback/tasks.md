# Tasks: Route Endpoint Fallback

**Input**: Design documents from `/specs/006-route-endpoint-fallback/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Requested by the spec (SC-003: new fallback tests added, zero modifications to pre-existing behavior tests). Test tasks are written FIRST and MUST FAIL before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `backend/src/`, `frontend/src/`
- Backend code lives under `backend/apps/transport/`; zero frontend changes in this feature

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prove the untouched baseline before changing behavior

- [X] T001 Run the full backend suite green and record the baseline counts with `manage.py test` in `backend/` (no code changes; SC-003 baseline)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The single shared precedence rule that MUST exist before any story payload can use it

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 Implement the shared endpoint-annotation helper (`resolved_origin` / `resolved_destination` via `Coalesce(NullIf(Trim(...)))` over first/last ordered-stop subqueries, beside `routes_with_master_fields`) in `backend/apps/transport/api/views.py`
- [X] T003 Switch `origin`/`destination` serializer sources from `from_text`/`to_text` to the annotation in `backend/apps/transport/api/serializers.py` (depends on T002 for the annotation names; wire shape unchanged per `specs/006-route-endpoint-fallback/contracts/endpoint-fallback.md`)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Route detail names its endpoints (Priority: P1) 🎯 MVP

**Goal**: Detail of a tag-less route with stops serves endpoint stop names; stored text wins; stop-less routes stay null

**Independent Test**: Open the detail of a servable route with blank stored text and recorded stops; origin equals the first ordered stop's name and destination the last (quickstart §1)

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T004 [P] [US1] Fallback tests for route detail (tag-less → endpoint names, stored-text precedence byte-identical, stop-less stays null, single-stop same name twice) in `backend/apps/transport/tests/test_read_routes.py`

### Implementation for User Story 1

- [X] T005 [US1] Apply the shared helper in the `route_detail` payload in `backend/apps/transport/api/views.py` (depends on T002)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Cards, details, and evidence agree (Priority: P2)

**Goal**: List and connectivity serve the identical fallback so all three shapes carry the same origin/destination

**Independent Test**: For tag-less routes with stops, compare list, detail, and connectivity responses; all three carry endpoint stop names (quickstart §2)

### Tests for User Story 2 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T006 [P] [US2] Fallback and cross-shape agreement tests for the routes list in `backend/apps/transport/tests/test_read_routes.py` and for connectivity results in `backend/apps/transport/tests/test_connectivity.py`

### Implementation for User Story 2

- [X] T007 [US2] Apply the shared helper in the `route_list` and `connectivity` payloads in `backend/apps/transport/api/views.py` (depends on T002)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Honest performance bounds, contract pointer, and end-to-end validation

- [X] T008 Update the tightened per-view query-count bounds to cover the two added subqueries in `backend/apps/transport/tests/test_read_performance.py`
- [X] T009 [P] Record the fallback value rule as a pointer to the 006 delta doc in `specs/003-read-map-api/contracts/read-map-api.md` (docs-only; no 003 behavior change)
- [X] T010 Run the full backend suite green with `manage.py test` in `backend/` plus `specs/006-route-endpoint-fallback/quickstart.md` validation (SC-003: zero modifications to pre-existing behavior tests)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Shares the helper with US1; independently testable per shape

### Within Each User Story

- Tests (included per spec SC-003) MUST be written and FAIL before implementation
- Helper (Foundational) before payload wiring
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- T004 and T006 can run in parallel (different test files, both test-first against the Foundational helper)
- T009 (docs-only pointer) can run in parallel with any implementation task
- Once Foundational phase completes, both user stories can start in parallel (if team capacity allows)

---

## Parallel Example: User Story 1

```bash
# Test-first (must FAIL before T005):
Task: "Fallback tests for route detail in backend/apps/transport/tests/test_read_routes.py"

# Then wiring (depends on T002 + failing T004):
Task: "Apply the shared helper in the route_detail payload in backend/apps/transport/api/views.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001 baseline)
2. Complete Phase 2: Foundational (T002 helper + T003 serializer switch — CRITICAL, blocks all stories)
3. Complete Phase 3: User Story 1 (T004 tests-first, T005 wiring)
4. **STOP and VALIDATE**: Test User Story 1 independently (quickstart §1)
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (detail)
   - Developer B: User Story 2 (list + connectivity)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Zero frontend changes; zero migrations; zero modifications to pre-existing behavior tests
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
