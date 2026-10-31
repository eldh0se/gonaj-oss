# Tasks: Place Groups for Same-Named Stops

**Input**: Design documents from `/specs/009-place-groups/` (plan.md, spec.md, research.md, data-model.md, contracts/places.md, quickstart.md)

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Included — explicitly requested (spec Independent Tests + plan Kaloor/matrix tests + full-suite gate).

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm branch, docs, and baseline gates before any code change

- [X] T001 Verify branch `009-place-groups` and design docs exist in `specs/009-place-groups/` (plan.md, spec.md, research.md, data-model.md, contracts/places.md, quickstart.md)
- [X] T002 [P] Record backend baseline by running `python backend/manage.py test apps.journey apps.transport tests` in `backend/` (expect green before changes)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared invariants the stories build on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 [P] Audit current `search_stops`/`find_routes` semantics in `backend/apps/journey/tools.py` (confirm exactly-one-of `query`/`bbox`, `zoom_in`/`empty` shapes, `RESULT_LIMIT 100`, `MAX_BBOX_SPAN_DEGREES 0.5`, travelling-order check, `/routes/:id` evidence)
- [X] T004 [P] Confirm additive shape contract in `specs/009-place-groups/contracts/places.md` against `specs/004-journey-agent/contracts/journey.md` (no existing shapes altered, evidence stays frontend `/routes/:id` addresses)

**Checkpoint**: Foundation ready — grouping semantics and shape contract fixed, user story work can begin

---

## Phase 3: User Story 1 - Search shows place groups instead of identical buttons (Priority: P1) 🎯 MVP

**Goal**: A duplicated name returns one group per tight cluster with member count, centroid, spread, and bbox — never N identical bare buttons.

**Independent Test**: Search a name with several same-named stops; confirm grouped results with member counts, representative locations, spread in meters, and bboxes.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T005 [US1] Add Kaloor 2-group test in `backend/apps/journey/tests/test_places.py` (7 same-named stops in two far-apart clusters → exactly 2 groups; quote constraints verbatim: "member count" per group, "`spread_m` is the max pairwise haversine distance between members", "same normalized name beyond 150 m linkage forms a separate group")
- [X] T006 [US1] Add search-guard tests in `backend/apps/journey/tests/test_places.py` (oversized bbox returns `zoom_in` with zero groups; unknown name returns `empty`; query+bbox together errors; single-stop name returns one single-member group with `spread_m` 0)
- [X] T007 [US1] Add determinism test in `backend/apps/journey/tests/test_places.py` (same data twice → same group keys in the same order; quote constraint verbatim: "`key` is `"lowercased-stripped-name#index"`; unique within one response; stable for unchanged data")

### Implementation for User Story 1

- [X] T008 [US1] Implement `search_places` grouping in `backend/apps/journey/tools.py` (exactly-one-of `query`/`bbox` with `search_stops` semantics; cap 100 stops pre-grouping; normalize casefolded-stripped names; 150 m single-linkage haversine clustering in Python; centroid/bbox/`spread_m`; members in `(name, id)` order as `{id, name, lat, lon}`)
- [X] T009 [US1] Add `_haversine_m` helper in `backend/apps/journey/tools.py` (pure meters function reused by clustering and `spread_m`; no PostGIS dependency, SQLite-portable)

**Checkpoint**: US1 fully functional and independently testable — duplicated names group deterministically

---

## Phase 4: User Story 2 - Choose the right place using route hints (Priority: P1)

**Goal**: Every group lists its serving routes (or states none serve it); the pair matrix keeps only travelling-order pairs so group-to-group resolution has a ready engine.

**Independent Test**: Search a duplicated name; confirm every group lists serving routes; run the matrix over member IDs and confirm only viable travelling-order pairs appear.

### Tests for User Story 2 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T010 [US2] Add route-hint tests in `backend/apps/journey/tests/test_places.py` (quote constraints verbatim: "`route_count` is the exact count of distinct servable routes" while "`routes` lists serving routes ordered by name, capped at 10"; member with no serving routes still listed with empty hints)
- [X] T011 [US2] Add matrix direction test in `backend/apps/journey/tests/test_places.py` (route serves A→B: matrix over `{A,B}×{A,B}` returns `(A,B)` with `/routes/:id` evidence and never `(B,A)`; equal-id pairs are skipped, unknown-id pairs error like `find_routes`)

### Implementation for User Story 2

- [X] T012 [US2] Implement servable-route attach in `backend/apps/journey/tools.py` (per group, distinct routes via the shared `servable_routes` definition; `route_count` exact, `routes` first 10 by `(name, id)` as `{id, name}`)
- [X] T013 [US2] Implement `find_routes_matrix(from_ids, to_ids)` in `backend/apps/journey/tools.py` (shared pair helper with `find_routes`: servable + ordered membership + "`position[from] < position[to]`"; skip equal ids per pair; return only pairs with ≥1 route, each route with `/routes/:id` evidence)

**Checkpoint**: US1 and US2 both work independently — groups carry hints, matrix resolves viable pairs

---

## Phase 5: User Story 3 - Individual stops stay selectable inside a group (Priority: P2)

**Goal**: Every member remains individually listed with distinguishing detail and individually resolvable to its exact stop.

**Independent Test**: Open a group with opposite-side duplicates; confirm every member listed; resolve one member through the matrix and confirm the exact stop (not the centroid).

### Tests for User Story 3 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T014 [US3] Add member-identity tests in `backend/apps/journey/tests/test_places.py` (opposite-side duplicate pair lands in one group as two ordinary members with distinct ids and coordinates; quote constraint verbatim: "Every member stop MUST remain individually listed inside its group with distinguishing detail, and MUST remain individually selectable")
- [X] T015 [US3] Add exact-member matrix test in `backend/apps/journey/tests/test_places.py` (matrix over one member id vs a destination returns pairs keyed by that exact member id; nothing resolves to a centroid)

### Implementation for User Story 3

- [X] T016 [US3] Verify member passthrough in `backend/apps/journey/tools.py` (members carry `{id, name, lat, lon}` verbatim from canonical rows; no merging, averaging, or dropping of members inside a group)

**Checkpoint**: All user stories independently functional — grouping aids choice without hiding stops

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Regression gates and invariants across all stories

- [X] T017 [P] Run backend regression `python backend/manage.py test apps.journey apps.transport tests` in `backend/` (gate: all green including new `test_places.py`)
- [X] T018 Verify read-only, no-model, SQLite-portable invariants in `backend/apps/journey/tools.py` (no writes, no new packages, no PostGIS functions, no model/prompt/TOOL_SCHEMAS changes, `RESULT_LIMIT`/`MAX_BBOX_SPAN_DEGREES` untouched)
- [X] T019 Run `specs/009-place-groups/quickstart.md` validation (shell checks: Kaloor 2 groups, matrix direction, `zoom_in`/`empty`/error guards)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - US1 (P1) then US2 (P1) in priority order; US3 (P2) after (all share `tools.py` + `test_places.py` — coordinate edits, do not parallelize within one file)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational — no dependencies on other stories (MVP)
- **User Story 2 (P1)**: Can start after Foundational — extends US1 groups with route attach + matrix, independently testable via T010–T011
- **User Story 3 (P2)**: Can start after Foundational — hardens member identity, independently testable via T014–T015

### Within Each User Story

- Tests MUST be written and FAIL before implementation (T005–T007 before T008–T009; T010–T011 before T012–T013; T014–T015 before T016)
- Grouping (T008) before route attach (T012) logically; matrix (T013) after the shared pair semantics are confirmed
- Story complete and checkpoint-validated before moving to next priority

### Parallel Opportunities

- T002 (baseline suite) can run alongside T001 (docs check)
- T003 + T004 (code audit vs contract check, different files) can run in parallel
- T017 (regression) is independent of T018–T019 ordering only after code lands; T018 + T019 can run in parallel (different concerns)
- US phases share `backend/apps/journey/tools.py` and `test_places.py` — do NOT parallelize story implementation tasks in the same files

---

## Parallel Example: User Story 1

```bash
# Tests first, sequentially (same file):
# T005 then T006 then T007 in backend/apps/journey/tests/test_places.py

# Implementation (same file, sequential):
# T008 then T009 in backend/apps/journey/tools.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundational (T003–T004)
3. Complete Phase 3: User Story 1 (T005–T009)
4. **STOP and VALIDATE**: Duplicated names group deterministically with counts/centroid/spread/bbox
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → semantics and shapes fixed
2. Add US1 → names group into places (MVP!)
3. Add US2 → groups carry route hints; matrix resolves viable pairs (T010–T013)
4. Add US3 → members stay individually resolvable (T014–T016)
5. Polish → full suite green (T017–T019)

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done, stories proceed sequentially (single shared module):
   - Developer A: US1 tests + implementation (T005–T009)
   - Developer B: Reviews US1 while drafting US2 tests (T010–T011)
3. US2 implementation (T012–T013), then US3 (T014–T016)
4. Joint Polish (T017–T019)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable via its Independent Test
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint and validate the story independently
