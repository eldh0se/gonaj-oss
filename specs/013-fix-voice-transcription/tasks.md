# Tasks: Fix Voice Search Transcription

**Input**: Design documents from `/specs/013-fix-voice-transcription/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Included — required by the spec's acceptance criteria, the quickstart stubbed-suite scenario, and the repo's failing-tests-first norm. Write each test task FIRST and confirm it FAILS before its implementation task.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Add `httpx` to `backend/requirements.txt` and verify install (`../.venv/bin/python -c "import httpx"`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared transcription engine that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 [P] Provider unit tests stubbed at the `httpx` boundary in `backend/apps/journey/tests/test_meta.py` (success transcript, empty transcript, timeout then retry, connection error)
- [X] T003 Rewrite `transcribe_audio` in `backend/apps/journey/providers/meta.py` per `specs/013-fix-voice-transcription/contracts/asr-wire.md` (POST `https://api.meta.ai/v1/asr/transcribe`, `request` JSON part, `audio/wav` part, `Accept: application/json`, 20 s timeout, at most one retry, stop-name `keywords`, parse `TranscribeResponse.transcript`; depends on T002 failing first)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Successful dictation returns an editable transcript (Priority: P1) 🎯 MVP

**Goal**: Dictated speech returns a 200 transcript that lands in the editable field

**Independent Test**: Post a stubbed WAV dictation and confirm 200 with non-empty `transcript` plus `meta`; confirm only edited text reaches the journey endpoint

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T004 [US1] Endpoint success test in `backend/apps/journey/tests/test_transcribe.py` (WAV upload returns 200 with transcript and `meta`, non-WAV rejected before any model call)

### Implementation for User Story 1

- [X] T005 [US1] WAV filename/MIME/header validation (`*.wav`, `audio/wav`, mono 16-bit PCM at 16 or 24 kHz) and success wiring in `backend/apps/journey/views.py` (5 MB bound "at most 5 MB" enforced before any model call; depends on T003, T004)
- [X] T006 [P] [US1] Encode dictated audio as mono 16-bit PCM WAV at 24 kHz client-side in `frontend/src/components/JourneyPanel.jsx` (WebAudio decode-to-PCM with resampling, upload `question.wav`; on encode failure show the plain cannot-transcribe notice, upload nothing, keep the editable field focused; press-and-hold UX unchanged)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Invalid audio is refused plainly, never guessed (Priority: P1)

**Goal**: Missing/empty/undecodable/oversized audio gets the plain 400 with no transcript

**Independent Test**: Post each invalid shape and confirm the plain-language 400 with no transcript and no model call

### Tests for User Story 2 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T007 [US2] Invalid-shape tests in `backend/apps/journey/tests/test_transcribe.py` (missing part, zero-byte file, undecodable bytes, over-5 MB file, non-WAV MIME)

### Implementation for User Story 2

- [X] T008 [US2] Rejection branches in `backend/apps/journey/views.py` for every T007 shape (plain-language 400, never a guessed transcript; builds on T005)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Upstream outage and privacy hold under failure (Priority: P2)

**Goal**: Outage returns the plain cannot-transcribe message within budget; no audio/transcript/key retained or logged anywhere

**Independent Test**: Stub an outage, dictate, confirm the plain message after at most one retry; audit storage/logs/bundle for audio, transcript, or key material

### Tests for User Story 3 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T009 [US3] Outage plus privacy tests in `backend/apps/journey/tests/test_meta.py` (timeout/connection error → one retry then plain cannot-transcribe; root `test_logging.py` sweep stays green)

### Implementation for User Story 3

- [X] T010 [US3] Quickstart end-to-end validation pass per `specs/013-fix-voice-transcription/quickstart.md` (stubbed suite, WAV probe, manual dictation if a key is available); close any gaps found in `backend/apps/journey/providers/meta.py` or `backend/apps/journey/views.py`

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Full-suite proof and contract alignment

- [X] T011 Full backend suite green plus root log-sweep (`../.venv/bin/python manage.py test`), and confirm the transcribe contract in `specs/004-journey-agent/contracts/transcribe.md` still matches behavior

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
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - Builds on the US1 views wiring (T005) but is independently testable
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - May integrate with US1/US2 but is independently testable

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Provider before views; views before frontend handoff
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- T002 (provider tests) and T004-scoped endpoint test authoring touch different files from setup and can be drafted alongside it once the wire contract is fixed
- T006 (frontend WAV encode, `JourneyPanel.jsx`) is independent of all backend files and can run in parallel with Phases 2–4
- Once Foundational completes, US1/US2/US3 test tasks can be drafted in parallel (different concerns, shared files sequenced at implementation)

---

## Parallel Example: User Story 1

```bash
# T006 (frontend) runs in parallel with backend Phases 2-4 - no shared files:
Task: "Encode dictated audio as WAV client-side in frontend/src/components/JourneyPanel.jsx"

# Backend order stays sequential (shared files):
# T002 (tests) -> T003 (provider) -> T004 (tests) -> T005 (views)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (`httpx` dependency)
2. Complete Phase 2: Foundational (CRITICAL - provider engine + its tests)
3. Complete Phase 3: User Story 1 (endpoint success + frontend WAV)
4. **STOP and VALIDATE**: Dictate stubbed WAV, confirm 200 transcript in the editable field
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

---

## Phase 7: Convergence

**Purpose**: Pin two spec'd edge cases with regression tests and remove
a doc ambiguity found in the converge assessment (2026-11-02). No
behavior gaps: FR-001–FR-010, all acceptance scenarios, and SC-001–
SC-004 are satisfied (backend 198 green, frontend 64 green).

- [ ] T012 Add a missing-key regression test in `backend/apps/journey/tests/test_transcribe.py` proving an empty `MODEL_API_KEY` returns the plain cannot-transcribe 400 with no key name or reason in the body, per spec edge cases (partial)
- [ ] T013 Add an exact-bound test in `backend/apps/journey/tests/test_transcribe.py` proving a valid WAV of exactly 5 MB is not size-rejected (provider stub is reached), per spec edge cases (partial)
- [ ] T014 Clarify the "other rates get HTTP 503" parenthetical in `specs/013-fix-voice-transcription/data-model.md` and `specs/013-fix-voice-transcription/contracts/asr-wire.md` to state it describes the upstream endpoint only and that this backend returns the plain 400 before any model call, per `research.md` Decision 3 (partial)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Data-model constraints applied verbatim: "at most 5 MB", `audio/wav` only, `*.wav` filename, mono 16-bit PCM at 16 or 24 kHz (24 kHz preferred), 20 s timeout, "at most one retry", 100-name keyword cap
- No `sessionId` is sent; tests stub at the `httpx` boundary with no live network
