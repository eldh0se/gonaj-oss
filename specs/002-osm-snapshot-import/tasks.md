# Tasks: OSM Snapshot Import

**Input**: Design documents from `/specs/002-osm-snapshot-import/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Test tasks below are included because the feature REQUIRES them: the quickstart's automated path runs the transport suite against sample fixtures, and the spec's acceptance criteria (idempotent rerun, anomaly codes, provenance chain) are verified through it. This is requirement-mandated verification, not a TDD mandate.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Branch, app skeleton, fixtures, importer skeleton

- [X] T001 Checkout feature branch `002-osm-snapshot-import` from `main` in repository root before any implementation
- [X] T002 [P] Create transport app skeleton in `backend/apps/transport/` (`__init__.py`, `apps.py` with `TransportConfig`)
- [X] T003 [P] Copy the five sample snapshot files into `backend/apps/transport/tests/fixtures/osm/` as tracked test fixtures
- [X] T004 [P] Create importer package skeleton in `backend/apps/transport/importer/` (`__init__.py`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema, admin review surface, and command skeleton that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 Create all eight entities with verbatim data-model constraints in `backend/apps/transport/models.py` (`verdict` in `VALID`, `VALID_WITH_WARNING`, `MISSING_DATA`, `AMBIGUOUS`, `UNRESOLVED`; severity in `fatal`, `warning`, `info`; `position` 1-based contiguous; natural key (`osm_type`, `osm_id`); all five `OsmSnapshot` fields required), plus the initial migration
- [X] T006 Apply the migration and verify all eight tables exist, then register the models for anomaly review in `backend/apps/transport/admin.py`
- [X] T007 Create the command skeleton with parsed flags in `backend/apps/transport/management/commands/import_osm_snapshot.py` (`--snapshot-dir` required, `--report-path` default `./osm-import-report.json`, `--snapshot-label` default to the snapshot directory's base name)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Import the snapshot offline (Priority: P1) 🎯 MVP

**Goal**: Samples import with per-entity counts; rerun shows zero changes; no network I/O anywhere.

**Independent Test**: Run the command twice against the sample fixtures; the second report shows zero inserted/updated/deleted rows, and counts match the fixture contents (contracts/cli-import.md, contracts/import-report.md).

### Implementation for User Story 1

- [X] T008 [P] [US1] Implement order-preserving Overpass JSON parsing in `backend/apps/transport/importer/parse.py` (relation member order kept; only `role=platform` node members feed stop sequencing; road-geometry members excluded)
- [X] T009 [US1] Implement change-detecting upsert on (`osm_type`, `osm_id`) in `backend/apps/transport/importer/policy.py` (save only on field change; count inserted/updated/unchanged; sequential with T010 — shared file, not parallel-safe)
- [X] T010 [US1] Implement per-parent membership rebuild in `backend/apps/transport/importer/policy.py` (delete + bulk-recreate with contiguous `position`, preserved `source_index`)
- [X] T011 [US1] Implement the JSON report writer and console summary in `backend/apps/transport/importer/report.py` per `contracts/import-report.md`
- [X] T012 [US1] Wire parse → policy → report inside a single transaction in `backend/apps/transport/management/commands/import_osm_snapshot.py` (depends on T008–T011)
- [X] T013 [US1] Add sample-import and zero-change-rerun tests in `backend/apps/transport/tests/test_import.py`
- [X] T023 [US1] Add abort-path tests in `backend/apps/transport/tests/test_import.py` (missing required file and invalid JSON → exit code 1 with zero partial writes; intra-file duplicate OSM ID → fatal anomaly and blocked run)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Review import anomalies (Priority: P2)

**Goal**: Every deviation recorded with severity + stable code; blocked/quarantined/excluded records kept out of servable data; nothing silently repaired.

**Independent Test**: Import fixtures containing known anomalies; each appears with the correct severity and stable code, affected records are flagged/quarantined/blocked per disposition, and original source values are preserved verbatim.

### Implementation for User Story 2

- [X] T014 [US2] Implement the verdict engine and closed anomaly code set in `backend/apps/transport/importer/policy.py` (severities `fatal`/`warning`/`info`; dispositions block run / block record / quarantine / flag / note; no auto-fix paths)
- [X] T015 [US2] Implement quarantine and orphan-pool handling in `backend/apps/transport/importer/policy.py` (platform-less routes quarantined; master-less routes excluded but tracked; `UNRESOLVED` masters blocked) (depends on T014)
- [X] T016 [P] [US2] Add anomaly-code and disposition tests in `backend/apps/transport/tests/test_anomalies.py` (fatal block, duplicate-platform warning with order preserved, quarantine, orphan tracking, optional-file info)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Trace any record to its source (Priority: P3)

**Goal**: Every stored record resolves record → run → snapshot (all five fields) → recipe, with no gaps and no fabricated timestamps.

**Independent Test**: Pick any stored stop and route; follow references to exactly one run, one snapshot with `label`, `recipe_ref`, `source_timestamps`, `retrieved_at`, `imported_at`, and the recipe document.

### Implementation for User Story 3

- [X] T017 [US3] Wire provenance references through the import in `backend/apps/transport/importer/policy.py` (every row carries its run; snapshot rows carry all five mandated fields; absent source timestamps stay absent)
- [X] T018 [P] [US3] Add provenance-chain trace tests in `backend/apps/transport/tests/test_provenance.py`

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Docs, README, full-flow validation, invariant review

- [X] T019 [P] Write the operator runbook for real-snapshot imports in `docs/osm-import.md` (snapshot acquisition pointer, command invocation, report interpretation, rerun and rollback expectations)
- [X] T020 [P] Update `README.md` data-source section for this feature (snapshot import replaces manual preparation as the OSM path; provenance retained from day one)
- [X] T021 Run `specs/002-osm-snapshot-import/quickstart.md` validation end to end (fixtures suite, full-snapshot import + rerun, anomaly review, provenance spot-check, network-disabled proof)
- [X] T022 Review the importer for invariant violations: no socket/network imports in `backend/apps/transport/importer/`, no timetable-entity writes (constitution VIII), no silent-repair code paths, per `contracts/cli-import.md` non-goals

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately (T001 first: all work happens on the feature branch)
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phases 3–5)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (US1 → US2 → US3)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Extends the US1 pipeline with verdict dispositions; independently testable against fixture anomalies
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Provenance wiring is additive; traceable independently once any import runs

### Within Each User Story

- Parser and upsert tasks (T008–T010) are independent files; wiring (T012) comes last
- Policy engine (T014) before quarantine handling (T015)
- Provenance wiring (T017) before its trace test is meaningful, but the test file (T018) can be drafted in parallel
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel (T002–T004: different files)
- T008 and T011 can run in parallel (separate files); T009 → T010 run sequentially (shared `policy.py`); T012 integrates them
- T016 (anomaly tests) can run in parallel with T014–T015
- T018 (provenance tests) can run in parallel with T017
- Once Foundational completes, US1–US3 can start in parallel (if team capacity allows)
- Polish tasks marked [P] can run in parallel (T019–T020: different files)

---

## Parallel Example: User Story 1

```bash
# Launch the independent US1 tasks together (separate files):
Task: "Implement order-preserving Overpass JSON parsing in backend/apps/transport/importer/parse.py"
Task: "Implement the JSON report writer in backend/apps/transport/importer/report.py"
# Then implement sequentially (shared policy.py):
Task: "Implement change-detecting upsert in backend/apps/transport/importer/policy.py"
Task: "Implement per-parent membership rebuild in backend/apps/transport/importer/policy.py"
# Then integrate:
Task: "Wire parse → policy → report inside a single transaction in backend/apps/transport/management/commands/import_osm_snapshot.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (starting with T001 branch checkout)
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (offline import + rerun proof on fixtures)
4. **STOP and VALIDATE**: Import twice against fixtures; second report shows zero changes
5. Demo if ready (populated stops/routes/masters + report prove the pipeline)

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Demo (MVP: data loads offline, reruns clean)
3. Add User Story 2 → Test independently → Demo (anomalies surfaced, nothing silently fixed)
4. Add User Story 3 → Test independently → Demo (full provenance chain)
5. Polish → runbook + README + quickstart green + invariant review clean
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (parse/upsert/report + wiring)
   - Developer B: User Story 2 (verdict engine + quarantine)
   - Developer C: User Story 3 (provenance wiring + trace tests)
3. Stories complete and integrate independently; Polish last

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- T001 (branch checkout) carries the repository root as its scope instead of a file path: it is a deliberate process gate requested for this feature
- T003 copies the retained samples as tracked fixtures; the full `data/osm/gcda/` snapshot stays untracked and is exercised only via the manual quickstart path
- Test tasks are requirement-mandated (quickstart automated path + spec acceptance criteria), not a TDD mandate
- Each user story is independently completable and testable
- Commit after each task or logical group, on the feature branch
- Stop at any checkpoint to validate the story independently
- Avoid: vague tasks, same-file conflicts, cross-story dependencies that break independence

---

## Phase 7: Convergence

**Purpose**: Close verification gaps found by `/speckit-analyze` convergence assessment (all implementation complete and 15/15 tests green; these tasks lock in unproven acceptance paths)

- [X] T024 Block all socket creation (patch `socket.socket` to raise) and rerun the sample import in `backend/apps/transport/tests/test_import.py`, asserting success with identical counts per SC-006/US1-AC3 (partial)
- [X] T025 Add an optional-file-absent test in `backend/apps/transport/tests/test_import.py` (copy fixtures minus optional files to tmp, import, assert `OPTIONAL_FILE_MISSING` info anomalies and outcome `succeeded`) per US2-AC4 (partial)
- [X] T026 Assert input immutability in `backend/apps/transport/tests/test_import.py` (hash fixture files before and after import, assert unchanged) per FR-013 (partial)
- [X] T027 Record the `quarantined` flag on the Route entity in `specs/002-osm-snapshot-import/data-model.md` to match `backend/apps/transport/models.py` (partial)
