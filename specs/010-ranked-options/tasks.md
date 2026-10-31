# Tasks: Ranked Journey Options

**Input**: Design documents from `/specs/010-ranked-options/` (plan.md, spec.md, research.md, data-model.md, contracts/answer.md, quickstart.md)

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Included — explicitly requested (spec Independent Tests + plan KSRTC/mixed/no-times tests + full-suite gate).

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm branch, docs, and baseline gates before any code change

- [X] T001 Verify branch `010-ranked-options` and design docs exist in `specs/010-ranked-options/` (plan.md, spec.md, research.md, data-model.md, contracts/answer.md, quickstart.md)
- [X] T002 [P] Record backend baseline by running `python backend/manage.py test apps.journey apps.transport tests` in `backend/` (expect green before changes)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared rank inputs the stories build on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 [P] Audit rank inputs in `backend/apps/journey/` (confirm `tools.find_routes_matrix` pair shape, operator annotation via `routes_with_master_fields`, `resolved_origin` via `routes_with_endpoint_names`, existing `_verify_route`/`_FORBIDDEN_SHAPED`/repair semantics in `agent.py`)
- [X] T004 [P] Confirm additive answer contract in `specs/010-ranked-options/contracts/answer.md` against the `ok` shape in `specs/004-journey-agent/contracts/journey.md` (existing `answer`/`routes`/`meta` untouched; prose enumerates groups for old renderers)

**Checkpoint**: Foundation ready — matrix shape, operator/hint sources, and verifier semantics confirmed

---

## Phase 3: User Story 1 - See every verified option grouped by operator (Priority: P1) 🎯 MVP

**Goal**: Resolved journeys return all verified direct options grouped by operator in deterministic order — never a single forced route.

**Independent Test**: Ask a journey with several verified direct services; confirm every option appears grouped by operator with evidence links, in the same order on repeat.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T005 [US1] Add KSRTC-only ranking test in `backend/apps/journey/tests/test_ranked.py` (matrix over one-operator pairs yields KSRTC wording; quote constraint verbatim: "options ordered by `stop_count` ascending then route id ascending")
- [X] T006 [US1] Add mixed-operator grouping test in `backend/apps/journey/tests/test_ranked.py` (two operators yield 2 groups; unknown operator lands in `"Other services"` last; repeat call returns identical order)
- [X] T007 [US1] Add single-option test in `backend/apps/journey/tests/test_ranked.py` (quote constraint verbatim: "A single verified option MUST be returned as a one-item list with no invented companions")

### Implementation for User Story 1

- [X] T008 [US1] Implement rank-and-group policy in `backend/apps/journey/agent.py` (group matrix pairs by annotated `operator` with `"Other services"` last when null/blank; order options by `(stop_count, route id)`; prose `answer` enumerates the groups)
- [X] T009 [US1] Emit additive `option_groups` in `backend/apps/journey/agent.py` (per-operator entries with verified route, boarding/alighting stops, evidence, and `stop_count`; existing `answer`/`routes`/`meta` fields unchanged)

**Checkpoint**: US1 fully functional and independently testable — full verified choice set, deterministic order

---

## Phase 4: User Story 2 - Boarding guidance only when the data supports it (Priority: P1)

**Goal**: Boarding hints appear exactly where `resolved_origin`/`stop.name` support them; nothing invented anywhere.

**Independent Test**: Ask journeys with and without hint-supporting data; confirm hints appear only where supported and answer text stays free of times/transfers.

### Tests for User Story 2 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T010 [US2] Add boarding-hint tests in `backend/apps/journey/tests/test_ranked.py` (hint present naming the boarding point when supported; absent without invention when unsupported; quote constraint verbatim: "A boarding hint MUST appear only where the dataset supports it; stands MUST never be invented")
- [X] T011 [US2] Add no-times test in `backend/apps/journey/tests/test_ranked.py` (ranked answer text with hints passes `_FORBIDDEN_SHAPED`; assert no clock times, durations, or transfer wording)

### Implementation for User Story 2

- [X] T012 [US2] Implement dataset-gated boarding hints in `backend/apps/journey/agent.py` (hint text from `resolved_origin` + `stop.name` only; no stand mapping table; omit the field when unsupported)

**Checkpoint**: US1 and US2 both work — grouped options with honest hints

---

## Phase 5: User Story 3 - Destination options within the place region (Priority: P2)

**Goal**: Destination places offer each reachable member (capped at 5, evidence-linked) instead of one forced stop.

**Independent Test**: Ask into a multi-stop place; confirm every reachable member is offered and picking one resolves to that exact member.

### Tests for User Story 3 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T013 [US3] Add destination-member tests in `backend/apps/journey/tests/test_ranked.py` (multi-member destination yields reachable members in matrix order; quote constraint verbatim: "`destinations` holds at most 5 entries, each evidence-linked"; further options counted in prose, never listed; empty matrix with nothing verifiable refuses honestly with no listed options)

### Implementation for User Story 3

- [X] T014 [US3] Implement capped destination list in `backend/apps/journey/agent.py` (first 5 reachable members with evidence links; prose states the count of further options)

**Checkpoint**: All user stories independently functional — full options, honest hints, reachable destinations

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Regression gates and invariants across all stories

- [X] T015 [P] Run backend regression `python backend/manage.py test apps.journey apps.transport tests` in `backend/` (gate: all green including new `test_ranked.py`)
- [X] T016 Verify per-option verifier, repair, and no-PII logs in `backend/apps/journey/agent.py` (every option passes `_verify_route`; drafts get one repair attempt then refusal; `_FORBIDDEN_SHAPED` unchanged; logs carry model/provider/latency/tools only)
- [X] T017 Run `specs/010-ranked-options/quickstart.md` validation (multi-service grouping, hint presence/absence, destination cap, single-option list, refusal unchanged)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - US1 (P1) then US2 (P1) in priority order; US3 (P2) after (all share `agent.py` + `test_ranked.py` — coordinate, do not parallelize within one file)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational — no dependencies on other stories (MVP)
- **User Story 2 (P1)**: Can start after Foundational — attaches hints to US1 options, independently testable via T010–T011
- **User Story 3 (P2)**: Can start after Foundational — adds destination members, independently testable via T013

### Within Each User Story

- Tests MUST be written and FAIL before implementation (T005–T007 before T008–T009; T010–T011 before T012; T013 before T014)
- Grouping/ordering (T008) before hint attach (T012) logically; destination list (T014) last
- Story complete and checkpoint-validated before moving to next priority

### Parallel Opportunities

- T002 (baseline suite) can run alongside T001 (docs check)
- T003 + T004 (code audit vs contract check, different files) can run in parallel
- T015 (regression) is independent of T016–T017 ordering only after code lands; T016 + T017 can run in parallel (different concerns)
- US phases share `backend/apps/journey/agent.py` and `test_ranked.py` — do NOT parallelize story implementation tasks in the same files

---

## Parallel Example: User Story 1

```bash
# Tests first, sequentially (same file):
# T005 then T006 then T007 in backend/apps/journey/tests/test_ranked.py

# Implementation (same file, sequential):
# T008 then T009 in backend/apps/journey/agent.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundational (T003–T004)
3. Complete Phase 3: User Story 1 (T005–T009)
4. **STOP and VALIDATE**: Every verified option listed grouped by operator, deterministic order, one-item list for singles
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → inputs and contract fixed
2. Add US1 → full verified choice set (MVP!)
3. Add US2 → honest boarding hints (T010–T012)
4. Add US3 → reachable destination members (T013–T014)
5. Polish → full suite green (T015–T017)

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done, stories proceed sequentially (single shared module):
   - Developer A: US1 tests + implementation (T005–T009)
   - Developer B: Reviews US1 while drafting US2 tests (T010–T011)
3. US2 implementation (T012), then US3 (T013–T014)
4. Joint Polish (T015–T017)

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

**Purpose**: Close the single remaining plan gap found by `/speckit-converge` (contract bookkeeping only; all behavior converges)

- [X] T018 Document `option_groups` and `destinations` in the `ok` response section of `specs/004-journey-agent/contracts/journey.md` per plan: implementation note 2 (partial)
