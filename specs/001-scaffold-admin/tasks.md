# Tasks: Backend Admin Scaffold

**Input**: Design documents from `/specs/001-scaffold-admin/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Test tasks below are included because the spec REQUIRES them (FR-006: CI must run the backend test suite; Stories 2–3 define verifiable login/API behavior). This is requirement-mandated verification, not a TDD mandate.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Branch, project skeleton, and shared definitions

- [X] T001 Checkout feature branch `001-scaffold-admin` from `main` in repository root before any implementation
- [X] T002 [P] Create Django project skeleton in `backend/` (`backend/manage.py`, `backend/config/__init__.py`)
- [X] T003 [P] Create dependency files `backend/requirements.txt` and `backend/requirements-dev.txt` per research Decisions 2/4/8
- [X] T004 [P] Create database service definition in `compose.yml` (PostgreSQL 16 with PostGIS pre-enabled) per research Decision 3
- [X] T005 [P] Create React placeholder app in `frontend/` (`frontend/package.json`, `frontend/src/`) per research Decision 7

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core wiring that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T006 Configure Django settings with env-based PostgreSQL and fail-fast missing settings in `backend/config/settings.py`
- [X] T007 Wire root URLconf with admin and versioned API includes in `backend/config/urls.py`
- [X] T008 [P] Create core app shell in `backend/apps/core/` (`apps.py`, `urls.py`) to host cross-cutting endpoints

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Run the backend from a fresh clone (Priority: P1) 🎯 MVP

**Goal**: Install, migrate, createsuperuser, and runserver succeed end to end following only written docs.

**Independent Test**: On a clean machine, follow `docs/setup-backend.md` in order; the server starts with no undocumented steps (spec SC-001, SC-002).

### Implementation for User Story 1

- [X] T009 [US1] Apply migrations via `backend/manage.py` and verify clean apply plus re-run no-op (spec edge case) (verified on live Postgres 16: clean apply, rerun no-op)
- [X] T010 [US1] Verify `createsuperuser` via `backend/manage.py` produces a working admin account (verified: superuser created on live Postgres)
- [X] T011 [US1] Verify development server startup via `backend/manage.py` serves requests on the documented address (verified live HTTP: /api/v1/ 200, /api/v9/ 404, /admin/login/ 200)
- [X] T012 [US1] Write the fresh-clone setup guide in `docs/setup-backend.md` covering install, database start, migrate, createsuperuser, run

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Log into Django Admin (Priority: P1)

**Goal**: Superuser login at `/admin/login/` loads the dashboard; invalid credentials are denied with no session.

**Independent Test**: Log in with the superuser from US1; dashboard loads. Submit wrong credentials; access denied, no session created.

### Implementation for User Story 2

- [X] T013 [P] [US2] Add admin login verification test in `backend/tests/test_admin_login.py` (valid → dashboard; invalid → denied, no session)
- [X] T014 [US2] Verify admin dashboard loads and lists administration views at `/admin/login/` per `backend/config/urls.py` wiring (verified: full suite 5/5 on live Postgres includes login→dashboard; live GET /admin/login/ 200)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Reach the versioned API root (Priority: P2)

**Goal**: `GET /api/v1/` returns the discovery payload; unknown versions 404, per `contracts/api-root.md`.

**Independent Test**: Request `/api/v1/` → `200` with `{name, version}`; request `/api/v9/` → `404`.

### Implementation for User Story 3

- [X] T015 [P] [US3] Add API root contract test in `backend/tests/test_api_root.py` (200 payload shape, 404 unknown version)
- [X] T016 [US3] Implement version discovery view in `backend/apps/core/views.py`
- [X] T017 [US3] Route `/api/v1/` to the core view in `backend/apps/core/urls.py` (depends on T016)

**Checkpoint**: At this point, User Stories 1, 2 AND 3 should all work independently

---

## Phase 6: User Story 4 - Automated checks on every pull request (Priority: P3)

**Goal**: A CI workflow runs install, migration check, and the test suite on PRs with visible pass/fail.

**Independent Test**: Open a pull request; checks execute automatically and report results on the PR (healthy branch green, broken migration red).

### Implementation for User Story 4

- [X] T018 [US4] Create PR check workflow in `.github/workflows/ci.yml` (install → `makemigrations --check` → test suite)
- [X] T019 [US4] Open a verification pull request against the feature branch and confirm checks report pass/fail visibly on the PR (done: PR #1, backend CI job pass in 33s)

**Checkpoint**: All user stories should now be independently functional

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Docs consistency, full-flow validation, scope-guard review

- [X] T020 [P] Update `README.md` setup pointer to reference `docs/setup-backend.md` (replaces the "instructions later" placeholder for this feature)
- [X] T021 [P] Review `docs/setup-backend.md` for accuracy against the implemented flow, including database-start and failure-drill behavior (fixed CI working-directory paths in review)
- [X] T022 Run `specs/001-scaffold-admin/quickstart.md` validation end to end on a clean machine, including both failure drills (verified: migrate/createsuperuser/runserver/tests on live Postgres 16; both failure drills produce the specified errors; verification role/db dropped afterwards to leave host Postgres clean; USER-CONFIRMED: fresh run on owner machine after stopping host Postgres — superuser, /api/v1/, admin login all green)
- [X] T023 Review `backend/` and `frontend/` for transport-domain logic per spec SC-005 (must be absent) and confirm no public-account surface per spec FR-008 (clean: zero matches)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately (T001 first: all work happens on the feature branch)
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phases 3–6)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (US1 → US2 → US3 → US4)
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - Uses the superuser created in US1's flow, but testable independently once any superuser exists
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - Independently testable; no dependency on US1/US2
- **User Story 4 (P3)**: Can start after Foundational (Phase 2) - Meaningful once US1–US3 give the checks something to guard; verification PR (T019) needs the feature branch pushed

### Within Each User Story

- Test tasks (T013, T015) verify the story's acceptance scenarios and run in CI via T018
- Core implementation before integration (T016 before T017)
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel (T002–T005: different files)
- T008 (core app shell) can run in parallel with T006–T007
- Once Foundational completes, US1–US4 can start in parallel (if team capacity allows)
- T013 and T015 (test files) can run in parallel with each other
- Polish tasks marked [P] can run in parallel (T020–T021: different files)

---

## Parallel Example: User Story 3

```bash
# Launch the contract test together with the app shell work (different files):
Task: "Add API root contract test in backend/tests/test_api_root.py"
Task: "Create core app shell in backend/apps/core/"

# Then implement sequentially (view before route):
Task: "Implement version discovery view in backend/apps/core/views.py"
Task: "Route /api/v1/ to the core view in backend/apps/core/urls.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (starting with T001 branch checkout)
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (includes `docs/setup-backend.md`)
4. **STOP and VALIDATE**: Fresh-clone run on a clean machine per the independent test
5. Demo if ready (running server + docs prove the foundation)

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Demo (MVP!)
3. Add User Story 2 → Test independently → Demo (admin login proven)
4. Add User Story 3 → Test independently → Demo (versioned API proven)
5. Add User Story 4 → Test independently → Demo (PR checks guard everything)
6. Polish → README + docs consistent, quickstart green, scope-guard review clean
7. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (run flow + setup docs)
   - Developer B: User Story 2 (admin login + test)
   - Developer C: User Story 3 (API root + contract test)
3. Stories complete and integrate independently; US4 + Polish last

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- T001 (branch checkout) carries the repository root as its scope instead of a file path: it is a deliberate process gate requested for this feature
- T009–T011 are command-verification tasks executed via `backend/manage.py`; their "done" state is the verified outcome, recorded by checking them off
- Each user story is independently completable and testable
- Commit after each task or logical group, on the feature branch
- Stop at any checkpoint to validate the story independently
- Avoid: vague tasks, same-file conflicts, cross-story dependencies that break independence
