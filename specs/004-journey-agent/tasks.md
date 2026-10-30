# Tasks: Journey Agent

**Input**: Design documents from `/specs/004-journey-agent/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Requested by the spec (SC-001–SC-008: stubbed-model tests, no network), the plan (Django suite with stubbed model client, DRF test client, frontend component tests), and quickstart.md (automated suite in `apps/journey/tests/`). Test tasks are included per story, written first and FAIL before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `backend/apps/journey/`, `backend/config/`
- **Frontend**: `frontend/src/api/`, `frontend/src/components/`
- Backend reuses `backend/apps/transport/api/views.py` queryset helpers (`servable_routes`, `order_routes`, `routes_with_master_fields`, `routes_with_endpoint_names` from 006); zero import changes, zero migrations
- Frontend follows the 005 convention: REST client lives in `frontend/src/api/` (the plan's `services/journey.js` path is superseded by `api/journey.js`), one module per view in `frontend/src/components/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Server-side model dependency and untouched baseline before behavior changes

- [X] T001 Add the OpenAI Python SDK to `backend/requirements.txt` (server-side only; no model SDK in any frontend bundle)
- [X] T002 Run the full backend suite green and record the baseline counts with `manage.py test` in `backend/` (no code changes)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: App skeleton, declared-model configuration, provider client, and read-only tools that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Create the `journey` Django app skeleton (`__init__.py`, `apps.py`, `providers/__init__.py`, `tests/__init__.py`) in `backend/apps/journey/`, register it in `INSTALLED_APPS` in `backend/config/settings.py`, and mount the journey routes under `api/v1/` in `backend/config/urls.py`
- [X] T004 Declare server-only model configuration in `backend/config/settings.py`: `MODEL_API_KEY` fail-fast when absent (never in responses, logs, or the frontend bundle), declared IDs `muse-spark-1.3` (tool loop) and `muse-voice-transcribe-1.0` (transcription), 20 s model timeout
- [X] T005 Create the backend provider client in `backend/apps/journey/providers/meta.py` (OpenAI SDK with `base_url="https://api.meta.ai/v1"`, `Authorization: Bearer [REDACTED]` from server environment only)
- [X] T006 Implement the three read-only tools with MCP-compatible JSON schemas in `backend/apps/journey/tools.py`: `search_stops` (text/bbox over `Stop`, same semantics as the 003 stops list), `find_routes` (`from_stop_id`/`to_stop_id`, same-servable-route order-aware containment as 003 connectivity), `get_route_detail` (one route with ordered stops); reuse `servable_routes`, `order_routes`, `routes_with_master_fields`, and the 006 `routes_with_endpoint_names` (`resolved_origin`/`resolved_destination`) helpers; arguments outside the schema are rejected before execution and tools never write
- [X] T007 Create the thin REST client for the two journey endpoints in `frontend/src/api/journey.js` (POST journey with `question`/`history`/`context`, POST transcribe with the audio part; no model calls, no key)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Ask for a direct journey and get an evidence-grounded answer (Priority: P1) 🎯 MVP

**Goal**: Passenger asks in plain words and receives an evidence-verified direct-service answer naming boarding/alighting stops with `/routes/:id` evidence links and no times, or an honest refusal when no direct service is known

**Independent Test**: Ask about two stops sharing a direct route and confirm the answer cites that route with a working `/routes/:id` evidence link and contains no times; ask about an unconnected pair and confirm an honest refusal with no invented service (quickstart §1)

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T008 [US1] Stubbed-model contract tests for `POST /api/v1/journey/` answer and refusal shapes (status `ok` with named boarding/alighting stops plus `routes[]` evidence, status `refuse` with nothing invented, blank question returns the ask-again prompt without a model call) in `backend/apps/journey/tests/test_journey.py`
- [X] T009 [P] [US1] Component tests for answer rendering, evidence links, and refusal states in `frontend/src/components/JourneyPanel.test.jsx`

### Implementation for User Story 1

- [X] T010 [US1] Implement the tool loop, server-side verifier, and non-AI fallback in `backend/apps/journey/agent.py` (declared model `muse-spark-1.3`; every cited route must contain both resolved stops in travelling order on a servable route with `from_position < to_position`; any time-, duration-, frequency-, or transfer-shaped content fails verification with one repair attempt then refusal; 20 s timeout, one retry, then fallback with model `none` and provider `local-fallback`)
- [X] T011 [US1] Implement the journey endpoint in `backend/apps/journey/views.py` and routes in `backend/apps/journey/urls.py` (POST only, `AllowAny`, throttled 180/min and 5000/day via the shared `transport/api/throttling.py` classes with plain-language 429 plus `Retry-After` from the shared `transport/api/errors.py` shapes, GET and other verbs refused with 405; stateless per request with at most the last 6 history turns and `context.candidate_stop_ids` where stale ids are treated as unknown stops; evidence links use the frontend `/routes/:id` addresses)
- [X] T012 [US1] Create the chat panel and dock it in place of the inert 005 dock in `frontend/src/components/JourneyPanel.jsx` and `frontend/src/App.jsx` (everyday-language answer naming resolved boarding/alighting stops per FR-021, inline `/routes/:id` evidence links, plain-language refusal states; removes the `ChatDock` mount and deletes the now-obsolete `frontend/src/components/ChatDock.jsx`)
- [X] T013 [US1] Delete the superseded dock inertness test in `frontend/src/components/ChatDock.test.jsx` (the zero-fetch coming-soon assertion cannot hold now that the dock is active; panel behavior is covered by `frontend/src/components/JourneyPanel.test.jsx`)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Disambiguate when the request is unclear (Priority: P1)

**Goal**: Ambiguous stop names return candidate stops and ask the passenger to choose before any journey answer; unknown names get a plain not-found message with no invented stop

**Independent Test**: Ask with an ambiguous stop name and confirm the response names all candidates with no journey answer; pick one candidate and confirm the follow-up is evidence-grounded for the chosen stop; ask with an unknown name and confirm the plain not-found message (quickstart §2)

### Tests for User Story 2 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T014 [US2] Disambiguation tests for `POST /api/v1/journey/` (multiple matches return status `disambiguate` with all candidates and no route claims; follow-up with the chosen candidate answers or refuses honestly; unknown names return the not-found message with spelling-or-map guidance) in `backend/apps/journey/tests/test_journey.py`
- [X] T015 [P] [US2] Component tests for the candidate-choice prompt and follow-up answer rendering in `frontend/src/components/JourneyPanel.test.jsx`

### Implementation for User Story 2

- [X] T016 [US2] Implement disambiguation handling in `backend/apps/journey/agent.py` and `backend/apps/journey/views.py` (multiple stop matches return the candidate prompt directly without a model answer; disambiguation state travels in the request/response `context` payload with no server-side session, cache, or database writes)
- [X] T017 [US2] Wire candidate selection (naming the candidate or sending its id in `context.candidate_stop_ids`) through to the follow-up answer in `frontend/src/components/JourneyPanel.jsx` and `frontend/src/api/journey.js`

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Speak the request instead of typing it (Priority: P2)

**Goal**: Passenger dictates via Muse Voice Transcribe, edits the transcript before sending, the answer reflects the edited text, and zero audio bytes are retained anywhere

**Independent Test**: Dictate a journey question, edit a word in the transcript, and send; confirm the answer reflects the edited text and review confirms 0 bytes of audio retained on device beyond the session, server, or logs (quickstart §3)

### Tests for User Story 3 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T018 [P] [US3] Transcribe endpoint tests for `POST /api/v1/journey/transcribe/` (audio in returns `transcript` plus transcribe-model meta; missing, undecodable, or oversized over 5 MB audio returns the plain-language cannot-transcribe message with no guessed transcript; audio bytes discarded in the same request with nothing written to disk, database, cache, or logs) in `backend/apps/journey/tests/test_transcribe.py`
- [X] T019 [P] [US3] Component tests for the PUSH_TO_TALK voice button, editable transcript field, and edited-text send behavior in `frontend/src/components/JourneyPanel.test.jsx`

### Implementation for User Story 3

- [X] T020 [US3] Implement the transcribe endpoint in `backend/apps/journey/views.py` with transcription in `backend/apps/journey/providers/meta.py` (model `muse-voice-transcribe-1.0` with English bias plus stop-name vocabulary biasing built from the stop table at request time, capped to the highest-frequency names; 20 s timeout with one bounded retry; POST only, throttled, 405 for other verbs)
- [X] T021 [US3] Implement the voice button and editable transcript field in `frontend/src/components/JourneyPanel.jsx` (device microphone PUSH_TO_TALK UX posts audio to the transcribe endpoint; only the edited text is ever sent to `POST /api/v1/journey/`)

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: User Story 4 - See what the AI is and how it answered (Priority: P2)

**Goal**: Every journey response carries model ID, provider, and latency in its meta and the server log, and every AI-assisted answer renders distinctly labelled unverified

**Independent Test**: Ask any journey question and confirm meta carries model, provider, and `latency_ms`; find the matching server log line with the same three values plus the ordered `tools_used` list; confirm the UI answer renders distinctly labelled unverified with clickable evidence links (quickstart §4)

### Tests for User Story 4 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T022 [P] [US4] Meta and logging tests (journey and transcribe responses embed `meta: {model, provider, latency_ms}` measured around the producing call; the server log line records model, provider, latency, and ordered `tools_used`; fallback uses model `none` with provider `local-fallback`; logging never records prompts, answers, transcripts, or audio) in `backend/apps/journey/tests/test_meta.py`
- [X] T023 [P] [US4] Component tests for distinct AI styling and the persistent unverified label with clickable `/routes/:id` evidence links in `frontend/src/components/JourneyPanel.test.jsx`

### Implementation for User Story 4

- [X] T024 [US4] Emit response meta and server log lines in `backend/apps/journey/views.py` and `backend/apps/journey/agent.py` (fallback meta included; transcribe responses carry the voice model ID likewise)
- [X] T025 [US4] Render AI text in the distinct AI style with inline evidence links and the persistent unverified label in `frontend/src/components/JourneyPanel.jsx` and `frontend/src/App.css` (deterministic fallback and refusal states use the same label family; styling stays inside the 005 visual-identity tokens)

**Checkpoint**: All user stories should now be independently functional

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end validation, honest failure behavior, and constitution compliance across all stories

- [X] T026 Run `specs/004-journey-agent/quickstart.md` validation (§1–§6) with stubbed model clients plus the full backend suite (`manage.py test` in `backend/`) and the full frontend suite (`npm test` and `npm run build` in `frontend/`) green
- [X] T027 Verify read-only and open-access proof: stubbed-model write attempts blocked with 0 writes, identical results with no credentials, no model key in the frontend bundle and no direct frontend model calls, no Nominatim or external place search, throttle rates (shared `transport/api/throttling.py`) and 400/405/429 plain-language shapes (shared `transport/api/errors.py`) intact, and no N+1 queries against the shared 003/006 helpers (query-count bounds from 006 still hold)
- [X] T028 Verify AI-surface purity: no schedules, times, transfers, durations, or frequencies; no provenance, tags, OSM ids, or masters; no accounts, tracking, per-user memory, or personal data in storage or logs; review confirms the 005 palette, radius, and type scale with no new hues or webfonts

---

## Phase 8: Convergence

**Purpose**: Spec-home for shipped UI that the 004 artifacts never described

- [X] T029 Give the shipped From/To direct-search UI a spec home by recording the stop pickers, OR divider, single shared result area with mutual clearing, and picked-input styling in the 004 or 005 spec per user-requested UI (unrequested)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P1 → P2 → P2)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - Extends the US1 endpoint and loop with disambiguation; independently testable via its contract shapes
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - Adds the transcribe endpoint and voice UI; journey answering stays as in US1/US2
- **User Story 4 (P2)**: Can start after Foundational (Phase 2) - Adds meta, logs, and labelling over the US1–US3 surfaces

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Tool and provider work (Foundational) before the loop, the loop before endpoints, endpoints before panel wiring
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- T002 can run in parallel with T001 (baseline check vs dependency edit, different files)
- T009 can run in parallel with T008 (panel tests vs backend contract tests, different files)
- T015 can run in parallel with T014 (panel choice tests vs backend disambiguation tests, different files)
- T018 and T019 can run in parallel (transcribe endpoint tests vs voice UI tests, different files)
- T022 and T023 can run in parallel (meta/logging tests vs labelling tests, different files)
- Once Foundational completes, US2/US3/US4 can start in parallel with US1 wiring by different developers (shared-file edits to `agent.py`, `views.py`, and `JourneyPanel.jsx` must still land sequentially)

---

## Parallel Example: User Story 1

```bash
# Launch tests for User Story 1 together (test-first, different files):
Task: "Stubbed-model contract tests for POST /api/v1/journey/ in backend/apps/journey/tests/test_journey.py"
Task: "Component tests for answer rendering in frontend/src/components/JourneyPanel.test.jsx"

# Then implement sequentially (shared agent/view files):
Task: "Implement the tool loop, verifier, and fallback in backend/apps/journey/agent.py"
Task: "Implement the journey endpoint in backend/apps/journey/views.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently (quickstart §1)
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Add User Story 4 → Test independently → Deploy/Demo
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (loop, journey endpoint, panel)
   - Developer B: User Story 2 (disambiguation)
   - Developer C: User Story 3 (transcribe + voice UI)
   - Developer D: User Story 4 (meta, logs, labelling)
3. Stories complete and integrate independently (coordinate edits to the shared `agent.py`, `views.py`, and `JourneyPanel.jsx`)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Zero migrations: the agent is stateless, transcripts and audio are never stored, and all reads reuse the 003 servable helpers plus the 006 endpoint-name annotations
- Reuse, do not duplicate: `servable_routes`, `order_routes`, `routes_with_master_fields`, `routes_with_endpoint_names`; evidence addresses are the frontend `/routes/:id` pages built by 005, not `/api/v1/` URLs
- Avoid: model calls from the frontend, MCP server stand-up, schedule/time/transfer content, per-user memory or sessions, vague tasks, same-file conflicts, cross-story dependencies that break independence
