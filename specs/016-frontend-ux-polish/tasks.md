# Tasks: 016-frontend-ux-polish

**Input**: Design documents from `/specs/016-frontend-ux-polish/` (spec.md, plan.md, research.md, data-model.md, contracts/ui.md, quickstart.md)

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Spec pins vitest coverage per story Independent Test + FR-008 fallback — test tasks included, written FIRST and FAILED before implementation.

**Organization**: Tasks grouped by user story; each story independently testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `backend/src/`, `frontend/src/` — this feature is frontend-only; all paths under `frontend/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Baseline before any story work

- [X] T001 Run baseline `cd frontend && npm test` green on main and record result (71 passed, 2026-11-04)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared test/build scaffolding every story's suites rely on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 Add `__APP_VERSION__`/`__APP_SHA__`/`__APP_BUILT_AT__` global fallbacks in `frontend/src/test/setup.js` so every suite renders with defines missing (constraint: UI renders with all metadata absent)

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Scoped main search per tab (Priority: P1) 🎯 MVP

**Goal**: SearchBox renders inside Routes and Stops tab panels only; Journey tab shows none; debounce/pager/loading/no-match/error/sticky unchanged

**Independent Test**: Render with journey content, switch across tabs, confirm search appears only in Routes/Stops with working search + pager + sticky, never in Journey (contracts/ui.md C1)

### Tests for User Story 1 (write FIRST, FAIL before implementation)

- [X] T003 [P] [US1] Failing test: Journey tab renders no `role="search"` in `frontend/src/components/SearchBox.test.jsx` (ResultsList block; guard, passes pre/post)
- [X] T004 [P] [US1] Failing test: Routes and Stops tabs each render one scoped SearchBox sharing a single query state (tab switch preserves text) with independent working `Pager` in `frontend/src/components/SearchBox.test.jsx` (failed pre-fix, green post-fix)

### Implementation for User Story 1

- [X] T005 [US1] Render one `SearchBox` inside each of the Routes and Stops tab panels in `frontend/src/components/ResultsList.jsx`, hoisted so the Journey tab never receives one (shared query state, debounce 300ms unchanged)
- [X] T006 [US1] Remove the global `<SearchBox onQuery>` from the aside in `frontend/src/App.jsx` and pass query handlers into `ResultsList`
- [X] T007 [US1] Verify/adjust the sticky `.gonaj-search` rule to work inside tab panels in `frontend/src/App.css` (no behavior change to debounce, pager, error wording) — verified by inspection, selector still matches, no CSS change

**Checkpoint**: US1 fully functional and independently testable — Journey tab search-free, Routes/Stops share query + page independently

---

## Phase 4: User Story 2 - Compact mobile route detail (Priority: P1)

**Goal**: Mobile overlay capped at 50% viewport with internal scroll; close restores previously visible tab content; no collapse control; desktop dock untouched

**Independent Test**: Mobile viewport → height ≤50%, internal scroll, close returns previous tab content; desktop `min(400px,100%)` intact (contracts/ui.md C2)

### Tests for User Story 2 (write FIRST, FAIL before implementation)

- [X] T008 [P] [US2] Failing test: overlay capped at ≤50dvh with internal scroll and no collapse control, close restores tab content, in `frontend/src/components/RouteOverlay.test.jsx` and/or `frontend/src/App.test.jsx` (CSS cap failed pre-fix; close-restores test added)

### Implementation for User Story 2

- [X] T009 [P] [US2] Change the `max-width:48rem` `.gonaj-overlay` rule from `max-height:70dvh` to `50dvh` with internal `overflow-y:auto` in `frontend/src/App.css` (desktop rule untouched; scroll inherited from base rule, asserted)
- [X] T010 [US2] Ensure `frontend/src/components/RouteOverlay.jsx` exposes Close only (no collapse control) and close restores the previously visible tab with search state intact in `frontend/src/App.jsx` (verified: no code change needed, covered by new tests)

**Checkpoint**: US1 AND US2 both work independently

---

## Phase 5: User Story 3 - Map focuses on the selected route (Priority: P1)

**Goal**: Route open → only route polyline + stops, hidden area markers, fitted bounds, distinct origin/destination; stop card → center with markers staying; close → markers restored plus prior Journey candidate highlights restored when opened from disambiguation

**Independent Test**: Open overlay from Journey and Routes, assert focus rendering + labels + bounds, close asserts return of area markers plus prior candidate highlights when opened from Journey disambiguation; stop card centers with markers visible (contracts/ui.md C3)

### Tests for User Story 3 (write FIRST, FAIL before implementation)

- [X] T011 [P] [US3] Failing test: route open hides `area.markers`, fits bounds, origin/destination distinct + labeled, close restores markers plus prior candidate highlights when opened from Journey disambiguation, in `frontend/src/App.test.jsx` / `frontend/src/components/MapView.test.jsx` (3 tests failed pre-fix, green post-fix; candidateView untouched by construction so it resumes on close)
- [X] T012 [P] [US3] Failing test: stop card centers map via `center` with area markers staying, in `frontend/src/App.test.jsx`

### Implementation for User Story 3

- [X] T013 [US3] Wire focus props in `frontend/src/App.jsx`: while route detail open pass route-only `markers` + `highlight` + `fitBounds`, hide `area.markers`; on close restore them plus prior `candidateView` when opened from Journey disambiguation; on stop card pass `center` with markers intact
- [X] T014 [P] [US3] Render origin/destination markers distinctly (color/shape + accessible labels, not plain `circleMarker`) in `frontend/src/components/MapView.jsx` (labelled `L.marker` + divIcon pins, existing tokens)
- [X] T015 [US3] Restore generic area markers plus prior candidate highlights (when opened from Journey disambiguation) on overlay close in `frontend/src/App.jsx` (regression guard for T013 wiring) — verified via T011 close assertions, no extra code needed

**Checkpoint**: US1–US3 (all P1) independently functional — MVP scope complete

---

## Phase 6: User Story 4 - Discoverable press-and-hold dictation (Priority: P2)

**Goal**: Persistent `Press and hold to record` hint + tooltip; <~300ms tap shows inline explanation without capture; hold shows pulsing dot + live-region message with Ask disabled

**Independent Test**: Render button → hint/tooltip; quick-click → inline explanation, no recording; hold → dot + live-region + Ask disabled; release (contracts/ui.md C4)

### Tests for User Story 4 (write FIRST, FAIL before implementation)

- [X] T016 [P] [US4] Failing test: persistent hint + tooltip render, quick tap shows inline explanation with no `getUserMedia`/`MediaRecorder`/`postTranscribe` call, in `frontend/src/components/JourneyPanel.test.jsx` (failed pre-fix)
- [X] T017 [P] [US4] Failing test: hold shows pulsing dot + `Listening… release to send` (`role=status`) with Ask disabled, static dot under `prefers-reduced-motion`, in `frontend/src/components/JourneyPanel.test.jsx` (failed pre-fix; reduced-motion covered by CSS media query)

### Implementation for User Story 4

- [X] T018 [US4] Add persistent hint text + `title` and pointer-timestamp tap-vs-hold (<~300ms inline explanation, never starting capture) in `frontend/src/components/JourneyPanel.jsx` (hold-arms 300ms timer; tap cancels, capture never starts)
- [X] T019 [US4] Add recording-state UI (pulsing red dot, `Listening… release to send` live region, Ask disabled) in `frontend/src/components/JourneyPanel.jsx` plus dot + `prefers-reduced-motion` static fallback in `frontend/src/App.css`

**Checkpoint**: US4 independently functional alongside US1–US3

---

## Phase 7: User Story 5 - Direct and ask modes clear each other (Priority: P2)

**Goal**: Ask submit/transcribe-complete wipes direct state; direct input/select/Find wipes ask state; mid-selection abandonment clean both ways

**Independent Test**: Type question → start direct → ask cleared; set direct + submit ask (and transcribe) → direct cleared; half-made selections both ways (contracts/ui.md C5)

### Tests for User Story 5 (write FIRST, FAIL before implementation)

- [X] T020 [P] [US5] Failing tests both directions incl. mid-selection abandonment in `frontend/src/components/JourneyPanel.test.jsx` (both failed pre-fix; incl. transcribe-clears-direct test)

### Implementation for User Story 5

- [X] T021 [US5] Implement bidirectional resets in `frontend/src/components/JourneyPanel.jsx`: ask submit/transcribe-complete clears `fromText/fromStop/toText/toStop` + candidate menus + `direct`; direct typing/selecting/Find clears `question` + ask `state/cards/paging/filter` + candidate map highlights via `onShowCandidates(null)` (Find with incomplete picks keeps ask intact — no search started)

**Checkpoint**: US5 independently functional

---

## Phase 8: User Story 6 - Ask in progress locks direct mode (Priority: P2)

**Goal**: Ask loading disables From/To + selection + Find with no concurrent direct search; Stop aborts `askAbort`, restores idle, preserves question

**Independent Test**: Submit ask → controls disabled + Stop visible; Stop → idle with text intact, no direct fired; direct attempts during loading no-op (contracts/ui.md C6)

### Tests for User Story 6 (write FIRST, FAIL before implementation)

- [X] T022 [P] [US6] Failing test: loading disables direct controls + Stop aborts to idle preserving question with no direct search, in `frontend/src/components/JourneyPanel.test.jsx` (failed pre-fix)

### Implementation for User Story 6

- [X] T023 [US6] Disable From/To inputs, candidate selection, and Find while `state.status==loading`, add Stop button aborting `askAbort` (idle, question preserved), and guard `findDirectRoutes` against concurrent ask in `frontend/src/components/JourneyPanel.jsx` (candidate menus impossible while loading: ask submit clears direct text so no options render)

**Checkpoint**: US6 independently functional

---

## Phase 9: User Story 7 - Visible frontend version (Priority: P3)

**Goal**: Footer shows `v{version}+{sha7} · built <UTC>` when metadata exists, `v{version}` fallback otherwise

**Independent Test**: Render with metadata → full string; without → plain-version fallback (contracts/ui.md C7)

### Tests for User Story 7 (write FIRST, FAIL before implementation)

- [X] T024 [P] [US7] Failing test: `footer.gonaj-version[data-testid=app-version]` renders full string with metadata and `v{version}` fallback without, in `frontend/src/App.test.jsx` (failed pre-fix)

### Implementation for User Story 7

- [X] T025 [US7] Inject `__APP_VERSION__` (from `package.json:0.1.0`), `__APP_SHA__` (7-char, empty when unknown), `__APP_BUILT_AT__` (UTC) via `define` in `frontend/vite.config.js` (verified inlined in `vite build` bundle, `647f630` present)
- [X] T026 [US7] Render the footer version element with small muted styling in `frontend/src/App.jsx` and `frontend/src/App.css`

**Checkpoint**: All user stories independently functional

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Full validation, no regressions

- [X] T027 Run `quickstart.md` validation scenarios 1–7 end-to-end (scoped search, mobile cap, focus, dictate, mutual clear, lock, version) — scenarios 1,3–7 via suites; scenario 2 via CSS-rule tests + dock guard (real-device 390px check left to reviewer)
- [X] T028 [P] Full `cd frontend && npm test` green with no desktop visual regression (`min(400px,100%)` dock, tab layout, journey cards) — 8 files, 86 passed; only desktop addition is the spec-mandated footer bar

---

## Phase 11: User Story 8 - Marker name labels (Priority: P2)

**Goal**: Permanent stop-name labels on every marker once the in-bounds stop count drops to a readable handful (≤6), area and route-focus alike; crowded views stay bare

**Independent Test**: Uncrowded render → every marker carries the stop name; add markers past the threshold (or pan) → labels unbind; endpoints keep titles either way (contracts/ui.md C8). Threshold tuned 6 → 24 after phone field feedback (T032).

### Tests for User Story 8 (write FIRST, FAIL before implementation)

- [X] T029 [US8] Failing test: uncrowded markers bind permanent name tooltips, crowded markers bind none, `moveend` toggles, in `frontend/src/components/MapView.test.jsx` (extend leaflet mock with `bindTooltip`/`unbindTooltip`) — both failed pre-fix

### Implementation for User Story 8

- [X] T030 [US8] Track in-bounds stop count in `frontend/src/components/MapView.jsx` (`MAX_LABELLED_VISIBLE = 6`, recompute on markers change + `moveend`), bind/unbind permanent themed tooltips per `labelsOn`; add `.gonaj-marker-label` style in `frontend/src/App.css` reusing theme tokens (single-pass build with content-signature guard + ordered label effect; no extra renders)
- [X] T031 Final `cd frontend && npm test` green after US8 (all suites incl. new label tests) — 8 files, 88 passed
- [X] T032 [US8] Retune `MAX_LABELLED_VISIBLE` 6 → 24 in `frontend/src/components/MapView.jsx` (field feedback: too shy on phone) + recalibrate crowded test to 30 markers in `frontend/src/components/MapView.test.jsx` (failed pre-recalibration, green after) + update FR-010/AC5/SC-003/research/data-model/C8 to ≤24
- [X] T033 Final `cd frontend && npm test` green after retune — 8 files, 88 passed
- [X] T034 [US8] Failing test: 13–24 visible markers bind compact (`is-compact`) tooltips, ≤12 bind full-size, in `frontend/src/components/MapView.test.jsx` (failed pre-fix)
- [X] T035 [US8] Two-tier labels in `frontend/src/components/MapView.jsx` (`FULL_LABEL_MAX = 12`, mode `off|full|compact` replacing boolean) + `.is-compact` style in `frontend/src/App.css`, update FR-010/research/data-model/C8
- [X] T036 Final `cd frontend && npm test` green after two-tier labels — 8 files, 89 passed

**Checkpoint**: US8 independently functional; feature complete

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational completion; run sequentially in priority order (shared files: `App.jsx` in US1/US3/US7, `JourneyPanel.jsx` in US4/US5/US6, `App.css` across stories)
- **Polish (Phase 10)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US1 (P1)**: After Foundational - no other story dependencies
- **US2 (P1)**: After Foundational - independent (CSS + RouteOverlay; note T010 touches `App.jsx`, sequential with US1 done)
- **US3 (P1)**: After Foundational - independent behavior; sequential file order with US1/US2 `App.jsx` edits
- **US4 (P2)**: After Foundational - first `JourneyPanel.jsx` change; subsequent US5/US6 build on the same file sequentially
- **US5 (P2)**: After Foundational - same-file sequential with US4
- **US6 (P2)**: After Foundational - same-file sequential with US4/US5
- **US7 (P3)**: After Foundational - `App.jsx`/`App.css` sequential with US1–US3 edits
- **US8 (P2)**: After US1–US7 - touches `MapView.jsx`/`App.css` (sequential with US3 edits, already complete) and `MapView.test.jsx`

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- `App.jsx` wiring before/after `MapView.jsx` marker rendering (US3: T013 then T014 may parallelize — different files, no dependency; T015 verifies T013)
- Story complete before moving to next priority

### Parallel Opportunities

- T003 ∥ T004 (US1 tests, same new-or-existing suite — coordinate to avoid duplicate blocks; safest in one file edit, run together)
- T011 ∥ T012 (US3 tests, App vs MapView suites)
- T016 ∥ T017 (US4 tests, same JourneyPanel suite — same-file, run together)
- T013 ∥ T014 (different files: `App.jsx` vs `MapView.jsx`)
- T009 ∥ T010-start (CSS vs JSX, merge order CSS first)
- T028 ∥ T027-observation (suite run while manually validating quickstart)

---

## Parallel Example: User Story 1

```bash
# Launch US1 tests together (same suite file — implement both blocks, then run once):
Task: "Failing test: Journey tab renders no role=search in ResultsList/App suite"
Task: "Failing test: Routes and Stops tabs each render one scoped SearchBox with Pager"
```

## Parallel Example: User Story 3

```bash
# Different files, no dependency — run together:
Task: "T013 Wire focus props in frontend/src/App.jsx"
Task: "T014 Distinct origin/destination markers in frontend/src/components/MapView.jsx"
```

---

## Implementation Strategy

### MVP First (P1 stories: US1 + US2 + US3)

1. Complete Phase 1: Setup (T001 baseline green)
2. Complete Phase 2: Foundational (T002 define fallbacks — blocks all stories)
3. Complete Phase 3: US1 scoped search (T003–T007)
4. Complete Phase 4: US2 mobile cap (T008–T010)
5. Complete Phase 5: US3 route focus (T011–T015)
6. **STOP and VALIDATE**: P1 independently testable per quickstart scenarios 1–3 + `npm test`
7. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. Add US1 → test independently → Deploy/Demo
3. Add US2 → test independently → Deploy/Demo
4. Add US3 → test independently → Deploy/Demo (MVP!)
5. Add US4 → US5 → US6 (JourneyPanel sequence) → test each → Deploy/Demo
6. Add US7 (version) → test → Deploy/Demo
7. Polish (T027–T028) → final gate

### Parallel Team Strategy

Single implementer recommended (shared `App.jsx`/`JourneyPanel.jsx`/`App.css` across stories make parallel branches conflict-prone). If staffed: complete Setup + Foundational together, then Developer A takes US1→US2→US3 (`App.jsx` chain), Developer B takes US4→US5→US6 (`JourneyPanel.jsx` chain), Developer C takes US7 + Polish — with sequential merge in story order.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story independently completable and testable
- Tests fail before implementation (vitest explicitly requested by spec FR-008 + story Independent Tests)
- Same-file tasks (`App.jsx`, `JourneyPanel.jsx`, `App.css`, `JourneyPanel.test.jsx`) run sequentially even when adjacent phases look parallel
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same-file parallel edits, cross-story dependencies that break independence
- Total: 36 tasks (T001–T036); per story: Setup 1, Foundational 1, US1 5, US2 3, US3 5, US4 4, US5 2, US6 2, US7 3, Polish 2, US8 8
