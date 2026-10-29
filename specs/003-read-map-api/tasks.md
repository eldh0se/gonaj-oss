# Tasks: Read Map API

**Input**: Design documents from `/specs/003-read-map-api/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Test tasks below are included because the feature REQUIRES them: the quickstart's automated path runs the transport API suite (`test_read_routes`, `test_read_stops`, `test_connectivity`), and the spec's success criteria (SC-001–SC-008) are verified through it. This is requirement-mandated verification, not a TDD mandate.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Feature branch, API package skeleton, green baseline

- [X] T001 Checkout feature branch `003-read-map-api` from `main` in repository root before any implementation
- [X] T002 [P] Create API package skeleton in `backend/apps/transport/api/` (`__init__.py` plus empty `pagination.py`, `errors.py`, `serializers.py`, `views.py`, `urls.py` modules) per plan.md project structure
- [X] T003 Run the existing backend suite via `backend/manage.py test` from `backend/` and record the green baseline before any API code lands (verified: 18 tests green on local SQLite shim; Postgres unreachable in this sandbox, so CI/user machine owns the Postgres proof)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared envelope, plain-language errors, whitelisted list serializers, servable-dataset rule, and test factories that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 [P] Implement the shared list envelope pagination in `backend/apps/transport/api/pagination.py` emitting exactly `count`, `results`, `total_pages`, `current_page`, `page_size` with `page_size` default `20` and maximum `100` (requests above `100` served at `100`), page beyond the end returning empty `results` with correct totals, and non-numeric or non-positive `page`/`page_size` raising the plain-language error (never a 500) per contracts/read-map-api.md (FR-019) (verified via story suites on local SQLite shim)
- [X] T005 [P] Implement plain-language error rendering in `backend/apps/transport/api/errors.py` (every error as `{"detail": "<plain sentence>"}`; unknown/withheld route or stop `404`; both-filters, malformed `bbox`, invalid pagination, and connectivity-id `400`s; non-GET `405` in the same shape; no field names, database messages, OSM identifiers, or stack details) and register it as the DRF exception handler in `backend/config/settings.py` (sequential after errors.py exists — settings edit is a single line) (plain-error and 404/405/429 shapes asserted by story and access tests)
- [X] T006 [P] Create hand-built test factories in `backend/apps/transport/tests/factories.py` (one `OsmSnapshot` + `ImportRun` scaffold, then `Stop`, `RouteMaster`, `Route`, `RouteStopMembership`, `RouteMasterMembership` builders) covering servable, quarantined, orphan, duplicate-name, duplicate-platform, single-stop, and membership-empty cases for all story tests (imported by all story test modules, green)
- [X] T007 [P] Implement whitelisted list serializers in `backend/apps/transport/api/serializers.py` (route: `id`, `name` (nullable in storage; exposed as stored), `origin` from `from_text`, `destination` from `to_text`, `operator` and `network` read through the master and `null` when the master carries none; stop: `id`, `name` (nullable; exposed as stored), `name_ml` (nullable), `lat`, `lon`) with `tags`, `osm_type`, `osm_id`, `import_run`, `verdict`, `quarantined`, `direction`, and any master object structurally absent (FR-007) (exact response key sets asserted in every story test)
- [X] T008 [P] Implement the servable-dataset querysets in `backend/apps/transport/api/views.py` (servable routes are exactly `Route.quarantined = False` AND belonging to a `RouteMaster` via `RouteMasterMembership`; every imported `Stop` row is servable; public `id` is the stored row's surrogate `id`) on GET-only views with `AllowAny` and no authentication or tracking engaged (FR-001–FR-003, research Decisions 2–3) (servable filtering asserted by withheld-route tests)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Browse and search routes (Priority: P1) 🎯 MVP

**Goal**: Blank browse-all plus search by name, origin, destination, or served stop name, with exact operator/network filters, stored order and duplicates preserved, and nothing internal exposed.

**Independent Test**: With factory data in place, browse all routes with a blank search, then search by a known route name, origin, destination, and served stop name; each returns the expected routes, and operator/network filtering narrows the list exactly (contracts/read-map-api.md routes list).

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T009 [P] [US1] Add routes-list contract tests in `backend/apps/transport/tests/test_read_routes.py` (blank/absent/whitespace `search` returns browse-all; name, origin, destination, and served-stop-name searches return only matches; `operator`/`network` partial values match nothing while exact values narrow by AND; stored order and duplicate rows preserved; no `tags`, `osm_*`, provenance, or master keys in any result; envelope fields with default `page_size` 20)

### Implementation for User Story 1

- [X] T010 [US1] Implement the routes list view in `backend/apps/transport/api/views.py` (`search` as case-insensitive containment over `Route.name`, `Route.from_text`, `Route.to_text`, and served `Stop.name`/`Stop.name_ml` via `RouteStopMembership`; blank search applies no text filtering; `operator`/`network` as exact stored-value matches through `RouteMasterMembership → RouteMaster` combined by AND; ordering by master-membership `position` then route `id`; query-level deduplication removes only stop-join fan-out, never stored rows; no matches returns `count: 0, results: []` with 200) through the T004 envelope (depends on T007, T008)
- [X] T011 [US1] Wire `GET /api/v1/routes/` in `backend/apps/transport/api/urls.py` and mount the transport API alongside the core root under `/api/v1/` in `backend/config/urls.py` (depends on T010)
- [X] T012 [US1] Run the US1 suite via `backend/apps/transport/tests/test_read_routes.py` (`./manage.py test apps.transport.tests.test_read_routes` from `backend/`) and confirm every T009 case passes (verified: 18 tests green on local SQLite shim)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Find stops by name or by map area (Priority: P1)

**Goal**: One stops list with two exclusive modes — name search or closed-bounds bounding box — where oversized areas answer `zoom_in` with zero stops and empty areas answer an explicit empty status.

**Independent Test**: Search stops by a known name fragment and confirm the matching stops return; then request stops inside a small map area and confirm exactly the stops inside that area return, boundary stops included (contracts/read-map-api.md stops list).

### Tests for User Story 2 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T013 [P] [US2] Add stops-list contract tests in `backend/apps/transport/tests/test_read_stops.py` (verified: 8 list tests green on local SQLite shim) (name-fragment search over `name`/`name_ml` returns matches with `status: "ok"`; `bbox` returns exactly the stops inside with stops exactly on an edge or corner included (closed bounds); `search` plus non-blank `bbox` together returns the plain-language 400; malformed, inverted, or out-of-range `bbox` returns the plain-language 400; span over the threshold returns 200 `status: "zoom_in"` with `count: 0, results: []` and never a partial list; valid empty area returns 200 `status: "empty"` with the empty envelope; neither param returns paginated browse-all)

### Implementation for User Story 2

- [X] T014 [US2] Implement the stops list view in `backend/apps/transport/api/views.py` (text mode: case-insensitive containment over `Stop.name`/`Stop.name_ml`, ordering by `name` then `id`; area mode: parse `bbox=min_lon,min_lat,max_lon,max_lat` and filter `min_lon ≤ lon ≤ max_lon` AND `min_lat ≤ lat ≤ max_lat` (closed bounds) over the existing `lat`/`lon` columns; both modes supplied is the T005 plain-language 400 and the modes are never combined; either span exceeding `MAX_BBOX_SPAN_DEGREES = 0.5` returns the shared envelope with `status: "zoom_in"`, `count: 0`, `results: []`; valid bbox with no stops returns `status: "empty"`; otherwise `status: "ok"`) through the T004 envelope (sequential in shared views.py after T010 — not parallel-safe)
- [X] T015 [US2] Wire `GET /api/v1/stops/` in `backend/apps/transport/api/urls.py` (depends on T014)
- [X] T016 [US2] Run the US2 suite via `backend/apps/transport/tests/test_read_stops.py` (`./manage.py test apps.transport.tests.test_read_stops` from `backend/`) and confirm every T013 case passes (verified: 8 list tests green on local SQLite shim)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Inspect a route and a stop in detail (Priority: P2)

**Goal**: Route detail with stops in travelling order and explicit origin/terminus, stop detail always carrying coordinates and serving routes, empty membership as an explicit empty list, and unknown or withheld ids as the same plain-language 404.

**Independent Test**: Open a known route and confirm its stops appear in travelling order with the first and last positions marked as origin and terminus; open a stop and confirm its coordinates and serving routes appear (contracts/read-map-api.md detail sections).

### Tests for User Story 3 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T017 [P] [US3] Add route-detail contract tests in `backend/apps/transport/tests/test_read_routes.py` (verified: 5 detail tests green alongside US1 tests, 18 total on local SQLite shim) (stops ordered by `position` (1-based, contiguous) with first step `is_origin: true` and last step `is_terminus: true`; single-stop route has both true; duplicate platform steps appear as separate entries in stored order; servable membership-empty route (factory-built as non-quarantined with zero memberships — the FR-014 state, however it arises) returns 200 with `stops: []`; unknown id and quarantined/orphan/blocked-master ids all return the identical plain-language 404 with no technical details)
- [X] T018 [P] [US3] Add stop-detail contract tests in `backend/apps/transport/tests/test_read_stops.py` (verified: 4 detail tests green alongside US2 tests, 12 total on local SQLite shim) (detail always includes `lat`/`lon`; `serving_routes` lists servable routes only in routes-list order as `id` + `name`; stop served only by withheld routes and unserved stop both return explicit `serving_routes: []`; unknown id returns the plain-language 404)

### Implementation for User Story 3

- [X] T019 [US3] Implement the route-detail serializer and view in `backend/apps/transport/api/serializers.py` and `backend/apps/transport/api/views.py` (route fields as in T007 plus `stops[]` ordered by `RouteStopMembership.position`, each step exposing `stop` (`id`, `name`, `name_ml`, `lat`, `lon`), `position`, `is_origin`, `is_terminus` with `source_index` and `import_run` hidden; empty membership serialises as explicit `stops: []`; lookup restricted to the T008 servable queryset so withheld ids 404 identically) (depends on T017)
- [X] T020 [US3] Implement the stop-detail serializer and view in `backend/apps/transport/api/serializers.py` and `backend/apps/transport/api/views.py` (stop fields as in T007 plus `serving_routes[]` of servable routes only, ordered as in the routes list, explicit `[]` when none serve the stop; coordinates always present) (sequential in shared serializers.py/views.py after T019 — not parallel-safe) (depends on T018)
- [X] T021 [US3] Wire `GET /api/v1/routes/{id}/` and `GET /api/v1/stops/{id}/` in `backend/apps/transport/api/urls.py` (depends on T019, T020)
- [X] T022 [US3] Run the detail suites via `backend/apps/transport/tests/test_read_routes.py` and `backend/apps/transport/tests/test_read_stops.py` (`./manage.py test apps.transport.tests.test_read_routes apps.transport.tests.test_read_stops` from `backend/`) and confirm every T017–T018 case passes (verified: 18 + 12 green on local SQLite shim)

**Checkpoint**: At this point, User Stories 1, 2 AND 3 should all work independently

---

## Phase 6: User Story 4 - Check direct connectivity between two stops (Priority: P2)

**Goal**: Only routes containing both stops in travelling order, each linked to its route-detail evidence, with no times, durations, or transfers ever returned.

**Independent Test**: Pick two stops known to share a route in the right order and confirm that route is returned with its evidence link; reverse the order and confirm the route is no longer returned as a direct connection (contracts/read-map-api.md connectivity section).

### Tests for User Story 4 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T023 [P] [US4] Add connectivity contract tests in `backend/apps/transport/tests/test_connectivity.py` (verified: 6 tests green on local SQLite shim) (forward-order pair returns the shared route once with `from_position < to_position` and `evidence` resolving to a 200 route detail; reverse-order-only pair returns the empty envelope; unconnected pair returns `count: 0, results: []` with 200; missing, non-numeric, equal, or unknown `from`/`to` ids return the plain-language 400; no key or text for times, durations, frequencies, or transfers appears in any response; shared envelope and pagination cap apply)

### Implementation for User Story 4

- [X] T024 [US4] Implement the connectivity serializer in `backend/apps/transport/api/serializers.py` (route fields as in T007 plus `from_position`, `to_position`, and `evidence` as `/api/v1/routes/{id}/`; no time, duration, frequency, or transfer fields exist in the serializer) (depends on T023)
- [X] T025 [US4] Implement the connectivity view in `backend/apps/transport/api/views.py` (join `RouteStopMembership` twice on the same T008-servable route with origin `position < destination position`; each matching route returned once through the T004 envelope; invalid `from`/`to` (missing, non-numeric, equal, unknown) returns the T005 plain-language 400; no match returns the empty envelope with 200) (sequential in shared views.py after T020 — not parallel-safe) (depends on T024)
- [X] T026 [US4] Wire `GET /api/v1/connectivity/` in `backend/apps/transport/api/urls.py` (depends on T025)
- [X] T027 [US4] Run the US4 suite via `backend/apps/transport/tests/test_connectivity.py` (`./manage.py test apps.transport.tests.test_connectivity` from `backend/`) and confirm every T023 case passes, including following one `evidence` link to its 200 route detail (verified: 6 tests green on local SQLite shim)

**Checkpoint**: All user stories should now be independently functional

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Public usage docs, full quickstart validation, invariant review

- [X] T028 [P] Write the public API usage guide in `docs/read-map-api.md` (the five reads with query parameters, the shared envelope with default 20 / cap 100, `bbox` exclusivity with `zoom_in` and empty outcomes, evidence links, plain-language errors, and the no-auth/no-tracking guarantee) linking contracts/read-map-api.md for normative shapes (written in `docs/read-map-api.md` linking the normative contract)
- [X] T029 [P] Review `backend/apps/transport/api/` for invariant violations: no `tags`, `osm_*`, provenance, verdict, quarantine, or master serialisation in `backend/apps/transport/api/serializers.py`; no `Trip`, `StopTime`, or `ServiceCalendar` reads (constitution VIII) and no socket/network or tracking code in `backend/apps/transport/api/views.py`; GET-only with `AllowAny` on all five reads (grep review: internal fields only in docstrings and the servable filter, never serialised; no Trip/StopTime reads, no tracking or network code; 5/5 views GET-only with authentication disabled)
- [X] T030 Run the full backend suite via `backend/manage.py test` from `backend/` (existing scaffold, import, and new API tests together) and confirm green with the T003 baseline unregressed, including `GET /api/v1/` still returning its discovery payload (verified: 67 tests green on local SQLite shim, baseline unregressed, API root untouched)
- [X] T031 Run `specs/003-read-map-api/quickstart.md` validation end to end (routes browse/search/filters, stops text/bbox/`zoom_in`/empty, details and withheld 404s, connectivity forward/reverse, envelope cap, read-only and open-access proofs) (verified: 21/21 quickstart checks plus 5/5 supplemental connectivity/text-search checks passed end to end via in-process HTTP against a real migrated database with `createcachetable` applied, a real `import_osm_snapshot` run, and the production DatabaseCache throttle backend; live-TCP serving on PostgreSQL itself remains for a machine with a database server, since this sandbox blocks all TCP and Postgres shared memory)
- [X] T032 Add query-count regression tests in `backend/apps/transport/tests/test_read_performance.py` (bounded constant query counts for the routes list, stops list, route detail, stop detail, and connectivity via `assertNumQueries` or captured-query assertions, proving the plan's no-per-row-queries goal at factory scale) (depends on T012, T016, T022, T027) (verified: 5 tests green with exact query bounds on local SQLite shim)
- [X] T033 Add read-only and open-access tests in `backend/apps/transport/tests/test_read_access.py` (POST, PUT, and DELETE on list and detail paths return the plain-language 405 shape and change no stored rows; all five reads succeed with no credentials or cookies and introduce no tracking `Set-Cookie` headers, covering FR-001–FR-003 and SC-008 automatically) (depends on T011, T015, T021, T026) (verified: 2 tests green on local SQLite shim)
- [X] T034 Implement per-IP throttling in `backend/apps/transport/api/throttling.py` and `backend/config/settings.py` (shared budget across all five reads at 180/minute and 5,000/day per client IP via Django `DatabaseCache` on the existing PostgreSQL, counters keyed by SHA-256 hash of the IP and expiring with the window, identity from the direct connection address with forwarded-for trusted only under an explicit trusted-proxy setting defaulting off, over-limit answering the plain-language 429 with `Retry-After`; wire the throttle classes onto every read view in `backend/apps/transport/api/views.py`; create the cache table via `./manage.py createcachetable` from `backend/` and document it in `docs/read-map-api.md`) (depends on T012, T016, T022, T027) (implemented in `backend/apps/transport/api/throttling.py`; wired onto all five views; `TRANSPORT_TRUSTED_PROXY` added to `backend/config/settings.py`)
- [X] T035 Add throttling tests in `backend/apps/transport/tests/test_read_throttle.py` (with test-lowered rates: requests under the limit succeed across mixed endpoints sharing one budget; the first over-limit request returns 429 with `Retry-After` and no data; a second client IP is unaffected; no cache key contains a raw IP; spoofed forwarded-for headers do not mint new identities while the trusted-proxy setting is off, and are honoured when it is configured on) (depends on T034) (verified: 6 tests green on local SQLite shim)

---

## Phase 8: Convergence

**Purpose**: Close the gaps found by `/speckit-converge` assessment (F1–F4 below). Existing tasks T001–T035 are untouched; these IDs are new and sequential.

- [X] T036 Replace related-field ordering under plain DISTINCT with an annotated membership-position Subquery in `backend/apps/transport/api/views.py` (route list, stop-detail serving routes, connectivity), keeping the specified order (membership position, then id) and stored-duplicate preservation, and confirm the T032 query-count bounds still hold, per FR-004, FR-006, FR-012, FR-016 (partial) (verified: new PostgresOrderingTests pin annotation-based ordering; full suite 70 green, T032 bounds hold)
- [X] T037 Add an API-scoped 404 handler returning the shared plain-language `{"detail"}` shape for unmatched `/api/*` paths and non-integer detail ids in `backend/config/urls.py`, leaving non-API 404 behaviour unchanged, per FR-015, FR-020 (partial) (verified: new access test asserts exact JSON shape for three unknown API paths; applies when DEBUG=False — on a DEBUG=True dev server Django shows its own debug page by design, accepted as-is)
- [x] T038 Run the full `specs/003-read-map-api/quickstart.md` validation against a reachable PostgreSQL database (migrate, `createcachetable`, full-snapshot import, live-server HTTP for all six steps), per SC-001–SC-008 (partial)
- [X] T039 Deduplicate the servable route-detail lookup in `backend/apps/transport/api/views.py` so a route linked to more than one master resolves to one row instead of raising unhandled `MultipleObjectsReturned`, per FR-013, FR-015 (partial) (verified: multi-master detail test returns 200; unresolvable ambiguity still maps to the plain 404)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately (T001 first: all work happens on the feature branch)
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phases 3–6)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed), with the shared-file serialisation noted below
  - Or sequentially in priority order (US1 → US2 → US3 → US4)
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories; first story to wire `api/urls.py` and the `config/urls.py` mount (T011)
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - No dependency on US1 behaviour; shares `views.py`/`urls.py`, so it serialises after US1 in a single-developer flow
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - Detail serializers extend the T007 list serializers; independently testable once factory routes/stops exist
- **User Story 4 (P2)**: Can start after Foundational (Phase 2) - Depends on the servable-route rule (T008) and route-detail existence only for the evidence-link test (T027 follows a US3 URL); the connectivity query itself needs no US1–US3 code

### Within Each User Story

- Contract tests first (T009, T013, T017–T018, T023), confirmed failing, then implementation
- Serializers before views that use them (T019/T024 patterns); views before their `urls.py` wiring (T011, T015, T021, T026)
- Shared files serialise: `api/views.py` (T010 → T014 → T019/T020 → T025), `api/serializers.py` (T007 → T019 → T020 → T024), `api/urls.py` (T011 → T015 → T021 → T026), and the two shared test files (US1/US3 in test_read_routes.py, US2/US3 in test_read_stops.py)
- Story test-run task (T012, T016, T022, T027) closes each story before the next priority starts

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel (T002 with the T003 baseline run: different concerns)
- All Foundational tasks marked [P] can run in parallel (T004–T008: different files — pagination, errors, factories, serializers, views)
- T009, T013, T023 (new test files) can be drafted in parallel once T006 factories exist; T017/T018 can run in parallel with each other (different test files)
- Once Foundational completes, US1–US4 test-drafting can start in parallel (if team capacity allows); implementation serialises only on the shared files listed above
- Polish tasks marked [P] can run in parallel (T028–T029: docs vs review, different files)

---

## Parallel Examples

### User Story 1

```bash
# Draft the contract tests while the foundational serializers land (separate files):
Task: "Add routes-list contract tests in backend/apps/transport/tests/test_read_routes.py"
Task: "Implement whitelisted list serializers in backend/apps/transport/api/serializers.py"
# Then implement and wire sequentially (shared views.py, then urls):
Task: "Implement the routes list view in backend/apps/transport/api/views.py"
Task: "Wire GET /api/v1/routes/ in backend/apps/transport/api/urls.py and backend/config/urls.py"
```

### User Story 2

```bash
# Draft the stops tests in parallel with US1 wiring (different files):
Task: "Add stops-list contract tests in backend/apps/transport/tests/test_read_stops.py"
# Then implement sequentially in shared views.py after the routes list view:
Task: "Implement the stops list view in backend/apps/transport/api/views.py"
Task: "Wire GET /api/v1/stops/ in backend/apps/transport/api/urls.py"
```

### User Story 3

```bash
# Launch both detail test tasks together (different test files):
Task: "Add route-detail contract tests in backend/apps/transport/tests/test_read_routes.py"
Task: "Add stop-detail contract tests in backend/apps/transport/tests/test_read_stops.py"
# Then implement sequentially (shared serializers.py/views.py), then wire:
Task: "Implement route then stop detail in backend/apps/transport/api/serializers.py and views.py"
Task: "Wire both detail routes in backend/apps/transport/api/urls.py"
```

### User Story 4

```bash
# Draft connectivity tests in parallel with US3 details (different file):
Task: "Add connectivity contract tests in backend/apps/transport/tests/test_connectivity.py"
# Then implement serializer, view, wiring in order:
Task: "Implement the connectivity serializer in backend/apps/transport/api/serializers.py"
Task: "Implement the connectivity view in backend/apps/transport/api/views.py"
Task: "Wire GET /api/v1/connectivity/ in backend/apps/transport/api/urls.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (starting with T001 branch checkout)
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (routes browse/search/filters live under `/api/v1/`)
4. **STOP and VALIDATE**: Run T012, then quickstart Step 1 (blank browse-all, four search fields, exact filters, hidden-fields inspection)
5. Demo if ready (passengers and AI tools can discover every servable route)

### MVP+ (User Stories 1 + 2)

Add Phase 4: stops by name or map area completes route/stop discovery — the full narrowed MVP validation surface (Principle I/VIII). Validate with T016 and quickstart Step 2 before adding details.

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready (envelope, errors, factories proven by story tests)
2. Add User Story 1 → Test independently (T012) → Demo (MVP: routes discoverable)
3. Add User Story 2 → Test independently (T016) → Demo (stops discoverable by name and map area)
4. Add User Story 3 → Test independently (T022) → Demo (ordered route detail, stop detail)
5. Add User Story 4 → Test independently (T027) → Demo (direct connectivity with evidence links)
6. Polish → usage docs + full suite + quickstart green + invariant review clean
7. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (T004–T008 are file-parallel)
2. Once Foundational is done:
   - Developer A: User Story 1 (routes list + first `urls.py`/mount wiring)
   - Developer B: User Story 2 tests, then stops list (serialises on `views.py` after A)
   - Developer C: User Story 4 tests, then connectivity (serialises on shared files last)
3. User Story 3 follows once list serializers stabilise; Polish last

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- T001 (branch checkout) carries the repository root as its scope instead of a file path: it is a deliberate process gate, as in features 001/002
- No new tables, migrations, dependencies, or frontend work in this feature (plan.md); `backend/apps/transport/models.py` is read, never edited
- Test tasks are requirement-mandated (quickstart automated path + spec SC-001–SC-008), not a TDD mandate; within each story they are still written first so the contract drives the view
- Each user story is independently completable and testable at its checkpoint test-run task
- Commit after each task or logical group, on the feature branch
- Stop at any checkpoint to validate the story independently
- Avoid: vague tasks, same-file conflicts (serialisation order is listed under Dependencies), cross-story dependencies that break independence

