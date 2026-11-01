# Tasks: Agent-Based Area Search for Direct Journeys

**Input**: Design documents from `/specs/012-agent-based-search/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Included — the spec defines per-story "Independent Test" criteria with
acceptance scenarios, and quickstart.md documents 12 validation scenarios;
repo convention is factory + stubbed-provider journey tests written first.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `backend/apps/journey/` for implementation, `backend/apps/journey/tests/` for tests
- This feature touches `backend/` only; `frontend/` unchanged; no migration

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Baseline before changes

- [X] T001 Run baseline suite green: `cd backend && python manage.py test apps.journey` with no code changes

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Tool wiring that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 [P] Build the shared Kaloor-shape fixture helper (`setUpTestData`/factories in `backend/apps/journey/tests/test_area_search.py`: K1/K2 opposite sides ≤150m, K3 within 150m of the served stop, K4/K5 far group, one servable route through origin member → K1) for reuse by all story phases, and write failing unit tests for `distance_m` (known pair ≈ expected meters via `_haversine_m`) and `nearby_stops` (ascending `distance_m`, cap "at most 100 stops", default radius 500m, error above max 2000m, error on invalid coords)
- [X] T003 Implement `distance_m(lat1, lon1, lat2, lon2)` in `backend/apps/journey/tools.py` as a thin wrapper over `_haversine_m` (`R = 6371000.0`); return `{"ok": False, "error": ...}` on non-numeric input, never raise
- [X] T004 Implement `nearby_stops(lat, lon, radius_m)` now in `backend/apps/journey/tools.py`: default `radius_m = 500`, enforced maximum `2000` (above → `{"ok": False, "error": ...}`), DB bbox prefilter ± radius, `_haversine_m` filter, ascending `distance_m`, "at most 100 stops returned", error on invalid coordinates. Consumption for shared location is deferred to the next feature — do not wire location input in this feature
- [X] T005 Promote `search_places` + `find_routes_matrix` to `TOOL_SCHEMAS` + `_TOOL_DESCRIPTIONS` in `backend/apps/journey/tools.py` with no logic change, and add schemas for `distance_m` + `nearby_stops` per `specs/012-agent-based-search/contracts/tool-schemas.md`
- [X] T006 Register all four tools in `_TOOL_FUNCTIONS` in `backend/apps/journey/agent.py` and extend `_validate_tool_args`: `from_ids`/`to_ids` are non-empty int lists with all values ≥ 1; `lat` in [-90, 90], `lon` in [-180, 180]; `radius_m` in (0, 2000]

**Checkpoint**: Foundation ready — `T002` tests pass; all four tools callable through `execute_tool` and recorded in `tools_used` — user story implementation can now begin

---

## Phase 3: User Story 1 - Area-to-area question answered without a forced pick (Priority: P1) 🎯 MVP

**Goal**: Destination-ambiguous area questions resolve group-first and answer with exact stops, evidence, and walk notes — no pick prompt, no wrong-side refusal

**Independent Test**: Ask an area-to-area question whose destination has opposite-side duplicates plus a walkable mate; the answer names the exact stops, the route with its evidence link, and the walk note, with no pick prompt shown

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation (T009–T012)**

- [X] T007 [P] [US1] Failing flow test in `backend/apps/journey/tests/test_area_search.py`: stubbed model calling `search_places` → `find_routes_matrix` → `get_route_detail` answers "Aluva to Kaloor" with exact boarding/alighting stops + `/routes/:id` + walk note and no pick prompt (quickstart #1)
- [X] T008 [P] [US1] Failing wrong-side test in `backend/apps/journey/tests/test_area_search.py`: named side unserved but opposite same-group mate served → same answer shape, never an exact-id refusal (quickstart #2)

### Implementation for User Story 1

- [X] T009 [US1] Update `SYSTEM_PROMPT` in `backend/apps/journey/agent.py` from `specs/012-agent-based-search/dev-notes/agent_instructions.md`: group-first rules, walk-note shape, refuse codes; matrix path replaces the `find_routes` mention
- [X] T010 [US1] Replace the selection full-entry `answer_direct` call with matrix-flow entry in `run_journey` in `backend/apps/journey/agent.py`; `answer_direct` stays as leaf verifier only, never as the entry answer (FR-011)
- [X] T011 [US1] Replace `_remaining_from_question` single-stop `search_stops` derivation with `search_places` group derivation in `backend/apps/journey/agent.py` (singleton group is the degenerate case, not a shortcut)
- [X] T012 [US1] Implement per-route classification + walk-note prose in `backend/apps/journey/agent.py` per `specs/012-agent-based-search/contracts/answer-shape.md`: same-group mates with "`d <= 150m`" inclusive via `distance_m`, "at most the 3 nearest" mates per end plus overflow count, "`walk_m` in whole meters" rounded half up, "at most 5 destinations" ranked operator group → stop count → route id; extend `_rank_pairs` options with `also_nearby`
- [X] T013 [US1] Run US1 tests green: `cd backend && python manage.py test apps.journey.tests.test_area_search` (quickstart #1, #2, distance part of #10)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Origin ambiguity handled the same way (Priority: P2)

**Goal**: Ambiguous origins resolve with the identical group-first flow, symmetric walk notes on the boarding end

**Independent Test**: Ask a question whose origin has same-named duplicates; the answer resolves them with the same exact-stop-plus-walk-note shape as destination-ambiguous ones, with no pick prompt when a walkable boarding stop serves

### Tests for User Story 2 ⚠️

- [X] T014 [P] [US2] Failing origin-ambiguity test in `backend/apps/journey/tests/test_area_search.py`: duplicated origin name resolves with exact boarding stop + walk note and no pick prompt (quickstart #3)

### Implementation for User Story 2

- [X] T015 [US2] Extend classification and answer prose to boarding-end mates (shared with T012; verified by T014) (`also_nearby_boarding`) with symmetric verification in `backend/apps/journey/agent.py`, reusing the US1 loop (symmetric by construction)
- [X] T016 [US2] Run US2 tests green: `cd backend && python manage.py test apps.journey.tests.test_area_search` (quickstart #3)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Pick prompt only after tools find nothing viable (Priority: P2)

**Goal**: Honest fallback — polite refusal when all tested pairs fail and the place matched; map/list pick when pairs went untested or the place never matched

**Independent Test**: A question with no direct route between any tested pair refuses politely; one with untested pairs or an unmatched place offers the map/list pick; one with a direct route shows no pick prompt

### Tests for User Story 3 ⚠️

- [X] T017 [P] [US3] Failing fallback tests in `backend/apps/journey/tests/test_area_search.py`: all-tested-fail → polite refusal; pair-cap truncation → pick; `empty` → pick for re-resolution; `zoom_in` → narrow-the-area request (quickstart #4–#7)
- [X] T018 [P] [US3] Failing no-bypass regression + audit tests in `backend/apps/journey/tests/test_area_search.py`: full selection context with wrong-side `selected_stop_id` answers via matrix, `answer_direct` never answers from the raw pair (quickstart #8); `tools_used` log line lists the new tools (quickstart #11)

### Implementation for User Story 3

- [X] T019 [US3] Implement fallback selection in `run_journey` in `backend/apps/journey/agent.py` per clarify outcome C: every-tested-pair-fails + place matched → refusal using the existing `_NO_DIRECT` message key verbatim; pairs untested or place never matched → map/list pick payload (`slot`, `offered_ids`, `resolved`, `slots`); `empty` → pick; `zoom_in` → narrow-or-map-prompt; replace `_disambiguation_context` flat-stop payloads with group-based payloads; extend `execute_tool` to record matrix pair findings (or rework `fallback()` to consume matrix pairs) with a fallback-with-matrix test pin; when the no-viable outcome follows explicitly picked exact stops, append a direct from-to search suggestion for familiar users (never auto-run it)
- [X] T020 [US3] Implement nearest-first pair ordering (minimum member-to-member stop distance across ends) with the 200-pair cap and farthest-first truncation at the matrix call site in `backend/apps/journey/agent.py` (research Decision 1); edit T010's matrix call site in place — single call site, no second matrix path
- [X] T021 [US3] Run US3 tests green: `cd backend && python manage.py test apps.journey.tests.test_area_search` (quickstart #4–#8, #11)

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Regression pins and full validation

- [X] T022 [P] Forbidden-content verifier test (covered by re-scoped `test_transfer_shaped_draft_is_refused_when_unrepairable`: transfer draft → one repair → refuse) in `backend/apps/journey/tests/test_area_search.py`: draft with a time/duration/transfer is rejected, gets one repair retry, then refuses (quickstart #12; verifier itself unchanged)
- [X] T023 Single-ended query regression test in `backend/apps/journey/tests/test_area_search.py`: `"Kaloor buses?"` keeps legacy behavior (quickstart #9; out of scope, must not change)
- [X] T024 Full validation run (journey 72 OK, transport 80 OK; quickstart #1–#12 each pinned by a test): `cd backend && python manage.py test apps.journey` green plus quickstart.md scenario walkthrough #1–#12
- [X] T025 Re-run related suites green (`apps.transport` tests) to confirm no shared-helper regressions from the `tools.py` additions

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phases 3–5)**: All depend on Foundational phase completion
  - Recommended order P1 → P2 → P2 (US2 reuses the US1 loop; US3's fallback consumes US1/US2 pair results)
  - May proceed in parallel once Foundational is done if staffed, respecting that order for integration
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) — no dependencies on other stories; this is the MVP
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) — reuses US1's matrix flow; independently testable via boarding-end scenarios
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) — consumes pair results shaped by US1/US2; independently testable via fallback scenarios

### Within Each User Story

- Tests MUST be written and FAIL before implementation (T007–T008 before T009–T012; T014 before T015; T017–T018 before T019–T020)
- Validators/wiring (Phase 2) before flow changes (US1) before fallback (US3)
- Story complete and green before moving to next priority

### Parallel Opportunities

- T007 + T008: independent test functions appended to the same new test file (coordinate appends)
- T017 + T018: independent fallback test functions, same convention
- T014 (US2 test) can be written in parallel with US1 implementation once Foundational is done
- T022 can be written any time after Foundational (pins unchanged verifier behavior)
- US1/US2/US3 implementation can be staffed in parallel after Foundational, integrated in priority order

---

## Parallel Example: User Story 1

```bash
# Launch US1 tests together (append-only test functions in test_area_search.py):
Task: "Failing flow test [US1] (T007)"
Task: "Failing wrong-side test [US1] (T008)"

# US1 implementation is sequential (single flow in agent.py):
# T009 → T010 → T011 → T012, then T013 green run
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001 baseline green)
2. Complete Phase 2: Foundational (T002–T006; CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1 (T007–T013)
4. **STOP and VALIDATE**: Test US1 independently (quickstart #1, #2)
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → foundation ready
2. Add User Story 1 → test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → test independently → Deploy/Demo
4. Add User Story 3 → test independently → Deploy/Demo
5. Polish → full quickstart validation → done
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (flow + destination answer)
   - Developer B: User Story 2 tests + boarding-end prose (integrates after A)
   - Developer C: User Story 3 tests + fallback (integrates after A)
3. Stories complete and integrate independently in priority order

---

## Notes

- [P] tasks = append-only test functions or different files, no ordering dependency
- [Story] label maps task to its user story for traceability
- Each user story is independently completable and testable via its quickstart scenarios
- Data-model constraints quoted verbatim in tasks (`d <= 150m`, `pos_from < pos_to` via `_direct_pair_routes`, caps) — not left to implementation discretion
- Verify tests fail before implementing; commit after each task or logical group
- Stop at any checkpoint to validate the story independently
