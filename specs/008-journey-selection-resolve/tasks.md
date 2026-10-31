# Tasks: Journey Selection Resolve

**Input**: Design documents from `/specs/008-journey-selection-resolve/` (plan.md, spec.md, research.md, data-model.md, contracts/selection.md, quickstart.md)

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Included — explicitly requested (spec Independent Tests + plan SelectionTests/frontend payload test + 125/53 regression gates).

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm branch, docs, and baseline gates before any code change

- [X] T001 Verify branch `008-journey-selection-resolve` and design docs exist in `specs/008-journey-selection-resolve/` (plan.md, spec.md, research.md, data-model.md, contracts/selection.md, quickstart.md)
- [X] T002 [P] Record backend baseline by running `python backend/manage.py test apps.journey apps.transport tests` in `backend/` (expect green before changes)
- [X] T003 [P] Record frontend baseline by running `npm test -- --run` in `frontend/` (expect green before changes)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared invariants and additive contract that all stories build on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 [P] Audit current selection path in `backend/apps/journey/agent.py` and pass-through in `backend/apps/journey/views.py` (confirm `run_journey` model loop, `_verify_route` order check, `_answer_payload`, `_NO_DIRECT`, log shape model/provider/latency/tools with no PII)
- [X] T005 [P] Apply additive contract delta from `specs/008-journey-selection-resolve/contracts/selection.md` to `specs/004-journey-agent/contracts/journey.md` (`disambiguate{slot, resolved:{id,name}, offered_ids}`, per-candidate `detail`, selection reply `{question, history[original], context{candidate_stop_ids, selected_stop_id, slot, resolved}}`, `meta{model:none, provider:local-fallback, resolution:selection}`; no removals, no new endpoints)

**Checkpoint**: Foundation ready — contract shapes fixed, baseline green, user story work can begin

---

## Phase 3: User Story 1 - Pick a stop once and get an answer or honest refusal (Priority: P1) 🎯 MVP

**Goal**: A valid single-end pick advances to a verified journey answer or honest refusal, never a repeat of the same candidate prompt.

**Independent Test**: Ask a one-end-ambiguous journey in `backend/apps/journey/tests/test_journey.py` style, receive the candidate list, pick one valid candidate, confirm the next response is `ok` (evidence-linked) or `refuse` — never the identical `disambiguate` prompt; frontend `frontend/src/components/JourneyPanel.test.jsx` confirms the pick request carries IDs/slot/context.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T006 [US1] Add SelectionTests single-end verified-answer tests in `backend/apps/journey/tests/test_journey.py` (duplicate-fixture same-named stops; click variant with valid `selected_stop_id` in `candidate_stop_ids`; typed variants with exact name and 1-based position deriving the same pick; assert `ok` names resolved stops, route evidence `/routes/:id`, `meta{model:none, provider:local-fallback, resolution:selection}`, zero model calls)
- [X] T007 [US1] Add SelectionTests single-end no-direct-route refusal test in `backend/apps/journey/tests/test_journey.py` (valid pick, empty `find_routes` result, assert `refuse` with no-direct-service message, `meta{model:none, provider:local-fallback}`, never a repeated prompt)

### Implementation for User Story 1

- [X] T008 [US1] Implement `_resolve_selection(context, question_text)` validation in `backend/apps/journey/agent.py` (quote constraints verbatim: "`selected_stop_id` must be `int` (reject `bool`, `str`, `None`) and a member of `candidate_stop_ids`", "`slot` must be `from` or `to`", "`resolved.id` must be `int` (reject missing/`None`/non-int `resolved`)"; when `selected_stop_id` is absent derive it by unambiguous text match of `question_text` against offered candidates in order — case-insensitive exact name or 1-based position/ordinal matching exactly one entry, else `None`; returns `(from_id, to_id)` or `None`)
- [X] T009 [US1] Implement selection fast-path at top of `run_journey` in `backend/apps/journey/agent.py` (on valid pair call `tools.find_routes` directly with manual tracker bookkeeping — `tracker["tools_used"].append("find_routes")` plus matching `calls`/`findings` entries so the audit matches the `execute_tool` shape; `_verify_route` each route for "`from_position < to_position` on a servable route"; return `_answer_payload` on first verified or `refuse` `_NO_DIRECT` when empty; set `meta` `model:none provider:local-fallback resolution:selection`; never call the model on this path)
- [X] T010 [P] [US1] Fix `choose`/`ask` payload in `frontend/src/components/JourneyPanel.jsx` (`choose(candidate,payload)` sends full payload plus `candidate_stop_ids`, `selected_stop_id`, `slot`, `resolved`; `ask()` preserves original question instead of forcing `history: []`; render path unchanged)
- [X] T011 [P] [US1] Extend frontend payload test in `frontend/src/components/JourneyPanel.test.jsx` (assert second request `context` carries IDs plus slot plus surviving context and `history` preserves the original question)

**Checkpoint**: US1 fully functional and independently testable — single-end picks resolve without model calls

---

## Phase 4: User Story 2 - Resolve both ends when both are ambiguous (Priority: P1)

**Goal**: First valid pick is retained and only the still-unresolved end is re-prompted; second valid pick yields a verified answer or honest refusal.

**Independent Test**: Ask a both-ends-ambiguous journey, pick the first end, confirm the helper prompts only for the remaining end (first pick retained, first prompt never repeated), pick the second end, confirm `ok` or `refuse`.

### Tests for User Story 2 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T012 [US2] Add SelectionTests both-ends-ambiguous flow test in `backend/apps/journey/tests/test_journey.py` (duplicate fixture for both ends, first valid pick returns prompt for remaining end only with `slots`/`surviving_context`, second valid pick returns verified answer or honest refusal, no identical repeat of the resolved end)

### Implementation for User Story 2

- [X] T013 [US2] Add disambiguation helper emitting slot identity in `backend/apps/journey/agent.py` (new helper — no existing `_disambiguation_context` in code; every `disambiguate` response carries `slot`, `offered_ids`, `resolved` where fixed, and per-candidate `detail` (`name_ml` or rounded coordinates); when no singletons exist return "`slots: {from_ids, to_ids}`" plus "`surviving_context: {other_end_ids}`" instead of "`(None, None)`")
- [X] T014 [P] [US2] Verify surviving-context round-trip and candidate detail in `frontend/src/components/JourneyPanel.jsx` (second pick carries retained first pick plus remaining `slot`; render candidate `detail` after the name when present; no new handlers)
- [X] T015 [P] [US2] Add two-step frontend flow test in `frontend/src/components/JourneyPanel.test.jsx` (first `choose` prompts remaining end only, second `choose` sends surviving context and renders verified answer or refusal)

**Checkpoint**: US1 and US2 both work independently — single-end and both-ends flows resolve

---

## Phase 5: User Story 3 - Invalid picks fail safely without inventing a journey (Priority: P2)

**Goal**: Forged, missing, or incomprehensible picks refuse safely with no invented stops/routes and no unbounded identical-prompt loop.

**Independent Test**: Trigger a candidate prompt, reply with a forged ID / missing `resolved` / gibberish, confirm safe `refuse` naming the problem plus a bounded next step; ask a fresh question mid-prompt and confirm stale candidates do not leak.

### Tests for User Story 3 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T016 [US3] Add SelectionTests invalid-pick refusal tests in `backend/apps/journey/tests/test_journey.py` (forged `selected_stop_id` not in `candidate_stop_ids` refuses safely; missing/non-int `resolved` refuses safely; ambiguous text matching zero or several candidates refuses safely; stale IDs refuse honestly; assert no invented stops/routes and no identical-prompt loop)
- [X] T017 [US3] Add fresh-question isolation test in `backend/apps/journey/tests/test_journey.py` (new journey question while a candidate prompt is pending starts fresh; stale `candidate_stop_ids` never leak into the new answer)

### Implementation for User Story 3

- [X] T018 [US3] Implement safe-refusal path for invalid selection in `backend/apps/journey/agent.py` (unmatched pick returns `refuse` stating the pick could not be matched plus a bounded next step; never invents stops/routes; each invalid reply refuses without an unbounded identical-prompt loop)
- [X] T019 [P] [US3] Verify post-selection evidence/content rules in `backend/apps/journey/agent.py` (quote constraints verbatim: "every cited route links to `/routes/:id` evidence", "answers contain no times and no transfers" via existing `_forbidden` check; same-road opposite-side duplicates stay ordinary distinct candidates with no extra confirmation loop)

**Checkpoint**: All user stories independently functional — valid, both-ends, and invalid flows behave per spec

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Regression gates and invariants across all stories

- [X] T020 [P] Run backend regression `python backend/manage.py test apps.journey apps.transport tests` in `backend/` (gate: all green; baseline 123 + 12 new SelectionTests = 135 OK)
- [X] T021 [P] Run frontend regression `npm test -- --run` in `frontend/` (gate: 53 passed)
- [X] T022 Verify additive contract, pass-through views, meta distinction, and no-PII logs in `specs/004-journey-agent/contracts/journey.md`, `backend/apps/journey/views.py`, `backend/apps/journey/agent.py` (no removed fields; selection `meta` carries `resolution:selection` while outage fallback carries none; no new handlers; tools stay read-only MCP-compatible; logs carry model/provider/latency/tools_used only)
- [X] T023 Run `specs/008-journey-selection-resolve/quickstart.md` end-to-end validation via `POST /api/v1/journey/` flows (ambiguous ask, valid pick, both-ends picks, forged pick, missing resolved, fresh question; confirm evidence links, no times/transfers, `none`/`local-fallback` meta)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - US1 (P1) and US2 (P1) then proceed in priority order; US3 (P2) after
  - Or in parallel if staffed (US1/US2/US3 touch shared `agent.py` — coordinate edits)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational — no dependencies on other stories (MVP)
- **User Story 2 (P1)**: Can start after Foundational — extends US1 fast-path with slots/surviving context, independently testable via T012
- **User Story 3 (P2)**: Can start after Foundational — hardens US1/US2 validation paths, independently testable via T016/T017

### Within Each User Story

- Tests MUST be written and FAIL before implementation (T006–T007 before T008–T009; T012 before T013; T016–T017 before T018)
- Validation helper (T008) before fast-path wiring (T009)
- Backend before frontend payload verification within US1 (T009 before T010–T011 logically; marked [P] as different files)
- Story complete and checkpoint-validated before moving to next priority

### Parallel Opportunities

- T002 + T003 (backend/frontend baselines, different suites) can run in parallel
- T004 + T005 (code audit vs contract edit, different files) can run in parallel
- T010 + T011 (panel fix vs panel test, different files in `frontend/src/components/`) can run in parallel
- T014 + T015 (panel round-trip vs flow test, different files) can run in parallel
- T020 + T021 (backend vs frontend regression) can run in parallel
- US phases share `backend/apps/journey/agent.py` — do NOT parallelize T008/T009 with T013/T018 in the same file without sequencing

---

## Parallel Example: User Story 1

```bash
# Backend tests first (sequential — same file):
# T006 then T007 in backend/apps/journey/tests/test_journey.py

# Frontend work in parallel (different files):
# T010: "Fix choose/ask payload in frontend/src/components/JourneyPanel.jsx"
# T011: "Extend frontend payload test in frontend/src/components/JourneyPanel.test.jsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational (T004–T005)
3. Complete Phase 3: User Story 1 (T006–T011)
4. **STOP and VALIDATE**: Single-end pick returns verified answer or honest refusal, never a repeated prompt; `meta none/local-fallback`; zero model calls on the path
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → contract and baselines ready
2. Add US1 → single-end selection resolves (MVP!)
3. Add US2 → both-ends flow retains first pick (T012–T015)
4. Add US3 → invalid picks refuse safely (T016–T019)
5. Polish → 125/53 gates green (T020–T023)

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: US1 backend (T006–T009 in `backend/apps/journey/`)
   - Developer B: US1/US2 frontend (T010–T011, T014–T015 in `frontend/src/components/`)
3. US2 backend extension (T013) lands after US1 fast-path; US3 hardening (T016–T019) last
4. Joint Polish (T020–T023)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable via its Independent Test
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint and validate the story independently
