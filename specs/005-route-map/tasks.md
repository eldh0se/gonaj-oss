# Tasks: Route Map

**Input**: Design documents from `/specs/005-route-map/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: The quickstart's automated suite (component tests via Testing Library with the Leaflet container mocked; no-network contract tests for `api/client.js` envelope handling) is the requested test coverage — test tasks are included per story, written first and failing before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `backend/src/`, `frontend/src/`
- All new code lives under `frontend/`; zero backend changes in this feature

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Frontend dependencies, test harness, and tile configuration

- [X] T001 Add `leaflet` and `react-router-dom` dependencies plus dev-only `vitest`, `@testing-library/react`, `jsdom`, and the `test` script in `frontend/package.json`
- [X] T002 [P] Create vitest/jsdom setup with Leaflet map-container mock in `frontend/src/test/setup.js`
- [X] T003 [P] Create tile provider config (OSM default URL, attribution, `VITE_TILE_URL` / `VITE_TILE_ATTRIBUTION` overrides; browser Referer satisfies OSMF self-identification, no server-side tile fetching) in `frontend/src/api/tiles.js`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: API boundary client and one-page shell that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Create fetch wrapper for 003 routes/stops/route-detail envelopes with `zoom_in`/`empty` handling, page-size cap 100, and plain-language errors in `frontend/src/api/client.js`
- [X] T005 [P] No-network contract tests for `api/client.js` envelope handling (`zoom_in`, `empty`, caps, errors) in `frontend/src/api/client.test.js`
- [X] T006 Rewrite router root (`/` map-browse, `/routes/:id` overlay, fallback to map-browse) in `frontend/src/main.jsx` and one-page layout (map + overlay + dock slot) in `frontend/src/App.jsx`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Browse stops and routes on the map (Priority: P1) 🎯 MVP

**Goal**: Passenger opens the map, sees their area's stops as markers, pans/zooms to explore, and taps a stop to see its serving routes — with zoom-in guidance for oversized areas and explicit empty states.

**Independent Test**: Load `/` over an area with known stops and confirm expected markers render once each; pan to an empty area and confirm the empty state; zoom out to a state-sized area and confirm zoom-in guidance with zero markers; stop the backend and confirm the plain-language cannot-load message (quickstart §1).

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T007 [P] [US1] Component tests for marker rendering, debounced area changes, stale-request discard, and `zoom_in`/`empty`/error states in `frontend/src/components/MapView.test.jsx`

### Implementation for User Story 1

- [X] T008 [P] [US1] Create Leaflet adapter (provider-isolated map instance, tile layer, markers, debounced viewport callback; never fetches transit data) in `frontend/src/components/MapView.jsx`
- [X] T009 [US1] Wire area changes to stops bbox query with debounce (~300 ms), `AbortController` stale discard, and `total_pages` follow-through until `count` satisfied in `frontend/src/App.jsx` (depends on T008)
- [X] T010 [US1] Implement stop selection showing name plus serving routes from stop detail, each linking to its overlay address, in `frontend/src/App.jsx`

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Search routes and stops by text (Priority: P1)

**Goal**: Passenger types a name fragment and gets only matching routes (each opening the detail overlay) and stops (picking one centres the map); blank search browses all; no-match states plainly; searches hit only the application's own endpoints.

**Independent Test**: Type a known route-name fragment and a known stop-name fragment and confirm only matches are offered; clear the search and confirm the full browse list returns; inspect traffic and confirm zero external place-search calls (quickstart §2).

### Tests for User Story 2 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T011 [P] [US2] Component tests for SearchBox debounce and ResultsList loading/empty/no-match/error states with own-endpoints-only traffic assertion in `frontend/src/components/SearchBox.test.jsx`

### Implementation for User Story 2

- [X] T012 [P] [US2] Create debounced (~300 ms) query input emitting query strings with no external calls in `frontend/src/components/SearchBox.jsx`
- [X] T013 [P] [US2] Create route/stop candidates list with loading, browse-all (paged), no-match hint, and error states in `frontend/src/components/ResultsList.jsx`
- [X] T014 [US2] Wire search to `api/client.js` routes/stops search (blank = browse-all) with route picks opening the overlay and stop picks centring the map in `frontend/src/App.jsx` (depends on T012, T013)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Inspect a route in the detail overlay (Priority: P2)

**Goal**: Passenger opens a route to see name, origin, destination, operator, network, ordered stops with marked origin/terminus, and map highlight — at a shareable `/routes/:id` address that opens the same overlay on direct load; empty membership and unknown ids handled plainly.

**Independent Test**: Open a route from search and confirm ordered stops with origin/terminus marked; copy the address, reload directly, and confirm the same overlay opens; open a stop-less route and an unknown id for the explicit statements (quickstart §3).

### Tests for User Story 3 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T015 [P] [US3] Component tests for ordered stops with origin/terminus, empty-membership statement, not-found state, and dismiss in `frontend/src/components/RouteOverlay.test.jsx`

### Implementation for User Story 3

- [X] T016 [P] [US3] Create route detail overlay (fields, ordered stops, origin/terminus marks, loading/empty/not-found states, dismiss) in `frontend/src/components/RouteOverlay.jsx`
- [X] T017 [US3] Wire `/routes/:id` to open the overlay on direct load, highlight the route on the map, and dismiss back to `/` in `frontend/src/App.jsx` (depends on T016)

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: User Story 4 - See where the journey chat will live (Priority: P2)

**Goal**: Map page includes the journey-chat dock region, visibly labelled as the future journey helper and marked coming soon; activating its control sends nothing, collects nothing, and stores nothing.

**Independent Test**: Load `/` and confirm the dock is present and labelled coming soon; activate it with network inspection and confirm zero requests, zero stored bytes, and the plain not-available message (quickstart §4).

### Tests for User Story 4 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T018 [P] [US4] Inertness tests asserting zero fetch calls and zero stored bytes on activation in `frontend/src/components/ChatDock.test.jsx`

### Implementation for User Story 4

- [X] T019 [US4] Create inert coming-soon chat dock (label, no-op entry control, not-available message; zero requests, zero storage) in `frontend/src/components/ChatDock.jsx` and mount it in the `frontend/src/App.jsx` layout

**Checkpoint**: All user stories should now be independently functional

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Responsive layout, tile-failure resilience, and end-to-end validation

- [X] T020 Single-column small-screen reflow CSS with all controls reachable plus tile-failure notice keeping markers/lists/overlay usable in `frontend/src/App.jsx` and `frontend/src/components/MapView.jsx`
- [X] T021 Run quickstart.md validation (§1–§5) and the full frontend suite green with `npm test` in `frontend/`, confirming zero backend changes and zero external place-search calls

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
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - May integrate with US1 but should be independently testable
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - May integrate with US1/US2 but should be independently testable
- **User Story 4 (P2)**: Can start after Foundational (Phase 2) - No dependencies on other stories

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Adapter/presentational components before App wiring
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- T005 can run in parallel with T004 (test and client are different files; test written first)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- Within each story, component tests and component implementation files marked [P] can start together (test-first, then wire-up depends on the component)
- T020 styling work can proceed alongside any single story's wiring

---

## Parallel Example: User Story 1

```bash
# Launch test and component together (test-first, different files):
Task: "Component tests for MapView in frontend/src/components/MapView.test.jsx"
Task: "Create Leaflet adapter in frontend/src/components/MapView.jsx"

# Then the wiring task after both:
Task: "Wire area changes to stops bbox query in frontend/src/App.jsx"
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
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
   - Developer D: User Story 4
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Zero backend changes: `backend/` is never touched in any task
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
