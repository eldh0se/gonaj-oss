# Feature Specification: OSM Snapshot Import

**Feature Branch**: `002-osm-snapshot-import`

**Created**: 2026-10-29

**Status**: Draft

**Input**: User description: "Offline OSM snapshot import for GCDA scope. Entities: OsmSnapshot, Stop, RouteMaster, Route, RouteStopMembership, RouteMasterMembership, ImportRun, ImportAnomaly. Rules: idempotent upsert on osm_type plus osm_id, contiguous position plus source_index, severity fatal warning info with stable codes, no silent repair, no geo filter, provenance entity to run to snapshot to recipe."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Import the GCDA snapshot offline (Priority: P1)

A data operator runs the import against the retained local snapshot
directory (`data/osm/gcda/`). With no network access, stops, routes,
route masters, and their memberships are loaded into the application's
own dataset, and re-running the same import changes nothing.

**Why this priority**: Nothing downstream (search, schedules, feedback)
can exist without the base transit dataset. Offline operation proves
the application owns its data rather than depending on live external
services (constitution V).

**Independent Test**: Run the import twice against the sample snapshot;
the second run reports success with zero row changes, and record counts
match the snapshot contents.

**Acceptance Scenarios**:

1. **Given** a snapshot directory with the three required files, **When**
   the operator runs the import with no network access, **Then** all
   stops, routes, route masters, and memberships are stored and the run
   reports success with per-entity counts.
2. **Given** a completed import, **When** the operator runs the same
   import again unchanged, **Then** the run succeeds with zero inserted,
   updated, or deleted rows.
3. **Given** a snapshot directory, **When** the import runs while the
   machine has no network route, **Then** the import still completes —
   it performs no network I/O.

---

### User Story 2 - Review import anomalies (Priority: P2)

A data steward reviews the anomalies recorded by an import: fatal
blockers (e.g. a master referencing a missing child route), warnings
(e.g. duplicate platforms, stray members, orphan routes), and
informational notes. Nothing is silently repaired — every deviation is
recorded with a stable code, and blocked or quarantined records stay
out of the servable dataset until fixed at the source.

**Why this priority**: The validation report shows the source data is
usable only with quarantine rules (464/465 masters importable, 1
blocked). Surfacing anomalies instead of hiding them is what makes the
dataset trustworthy.

**Independent Test**: Import the sample snapshot containing known
anomalies; every expected anomaly appears in the anomaly list with the
correct severity and stable code, and no affected record is silently
altered.

**Acceptance Scenarios**:

1. **Given** a master referencing a child route absent from the
   snapshot, **When** the import runs, **Then** a fatal anomaly is
   recorded and that master is blocked from the dataset.
2. **Given** a route with duplicate platform entries, **When** the
   import runs, **Then** the route is imported preserving original
   order with a warning anomaly — never silently deduped.
3. **Given** a route with no platform members, **When** the import
   runs, **Then** the route is quarantined (recorded, not served) with
   a warning anomaly.
4. **Given** optional snapshot files absent, **When** the import runs,
   **Then** an informational anomaly is recorded and the import still
   succeeds.

---

### User Story 3 - Trace any record to its source (Priority: P3)

A reviewer picks any stop, route, or membership and traces it back
through the import run and snapshot to the exact extraction recipe and
source-state timestamps that produced it.

**Why this priority**: Provenance is the one piece of future
architecture the constitution requires from day one (Principle V, VIII
data model). If the chain breaks now, later evidence-based processing
cannot reconstruct it.

**Independent Test**: Pick any stored record; follow its references to
the run, the snapshot (with label, recipe reference, timestamps, and
retrieval/import dates), and the recipe document.

**Acceptance Scenarios**:

1. **Given** any stored transit record, **When** its provenance is
   inspected, **Then** it resolves to exactly one import run, one
   snapshot, and one recipe reference with no gaps.
2. **Given** a stored `OsmSnapshot`, **When** its fields are inspected,
   **Then** `label`, `recipe_ref`, `source_timestamps`,
   `retrieved_at`, and `imported_at` are all present (constitution V).

---

### Edge Cases

- What happens when a required snapshot file is missing or is not
  valid JSON? The run fails fast with a fatal anomaly naming the file;
  no partial dataset from that run is served.
- What happens when the same `(osm_type, osm_id)` appears twice
  inside one snapshot file? A fatal anomaly is recorded and the run
  is blocked — duplicates indicate a corrupt extract, never a merge.
- What happens when a platform member references a stop ID absent
  from the stop file? A fatal anomaly is recorded for that stop-event,
  the event is excluded, and the route carries a warning flag.
- What happens when a snapshot is re-imported after the source files
  changed? It is recorded as a new snapshot and a new run; history is
  appended, never overwritten.
- What happens when master names collide across different master IDs?
  Both masters are imported under their own OSM IDs; a warning anomaly
  records the shared name. Identity is the OSM ID, never the name.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The import MUST run fully offline — no network I/O. It
  reads only a retained snapshot directory on local disk.
- **FR-002**: The snapshot directory MUST contain `osm_gcda_routes.json`,
  `osm_gcda_bus_stops.json`, and `osm_gcda_route_masters.json`; a
  missing or unparsable required file MUST abort the run with a fatal
  anomaly naming the file.
- **FR-003**: `osm_gcda_bus_stations.json` and
  `osm_gcda_route_members.json` are optional; absence MUST be recorded
  as an informational anomaly and MUST NOT fail the run.
- **FR-004**: Every entity MUST be upserted idempotently on the
  natural key (`osm_type`, `osm_id`); re-importing an unchanged
  snapshot MUST produce zero row changes.
- **FR-005**: Each membership row MUST store both `position` (1-based,
  contiguous within its parent after import-scope filtering) and
  `source_index` (the member's original index in the OSM relation).
- **FR-006**: Every anomaly MUST carry a severity of `fatal`,
  `warning`, or `info` and a stable machine-readable code from the
  defined code set (e.g. `CHILD_REF_MISSING`, `NO_PLATFORM_SEQUENCE`,
  `DUPLICATE_PLATFORM`, `STRAY_MEMBER`, `ASYMMETRIC_FROM_TO`,
  `ORPHAN_ROUTE`, `OPTIONAL_FILE_MISSING`, `DUPLICATE_MASTER_NAME`).
- **FR-007**: The import MUST NEVER silently repair source data: no
  deduping of duplicate platforms, no merging on duplicate names, no
  synthesis of missing children, no invented timestamps. Every
  deviation is recorded, quarantined, or blocked.
- **FR-008**: The import MUST apply no geographic filter of its own;
  the snapshot is treated as pre-scoped, and every in-scope element is
  processed.
- **FR-009**: Every stored record MUST resolve through the provenance
  chain record → `ImportRun` → `OsmSnapshot` → extraction recipe, with
  no gaps.
- **FR-010**: Every `OsmSnapshot` MUST carry `label`, `recipe_ref`,
  `source_timestamps`, `retrieved_at`, and `imported_at`, per
  constitution Principle V. Source-state timestamps are recorded only
  when present in the snapshot files, never fabricated.
- **FR-011**: The verdict policy from the validation report MUST be
  enforced: `UNRESOLVED` masters are blocked; `VALID WITH WARNING`
  records import with their flags; platform-less routes are
  quarantined; orphan routes are excluded from the master-driven
  dataset but tracked for later review.
- **FR-012**: Each run MUST produce a machine-readable import report
  with per-entity counts (inserted/updated/unchanged) and the full
  anomaly list with severities and stable codes.
- **FR-013**: Snapshot files are read-only input; the import MUST
  never modify files in place.

### Key Entities *(include if feature involves data)*

- **OsmSnapshot**: One retained Overpass extract batch. Attributes:
  `label`, `recipe_ref`, `source_timestamps` (per-file OSM base
  timestamps), `retrieved_at`, `imported_at`. A changed source file
  set is a new snapshot, never an edit.
- **Stop**: A bus stop platform (`node` with `highway=bus_stop`).
  Keyed by (`node`, OSM id); carries name, `name:ml`, coordinates,
  and amenity tags.
- **RouteMaster**: A `route_master` relation grouping direction
  variants. Keyed by (`relation`, OSM id); carries name, operator,
  network, verdict, and warning flags. Identity is the OSM ID, never
  the name.
- **Route**: A `route` relation (one direction/variant). Keyed by
  (`relation`, OSM id); belongs to one master; carries name, from/to,
  and verdict.
- **RouteStopMembership**: Ordered platform membership of a route.
  Carries `position` (contiguous) and `source_index` (original OSM
  member index). Ordered by platform-member order only; road-geometry
  (`way`) members are excluded from stop ordering.
- **RouteMasterMembership**: Child-route membership of a master,
  preserving source order. Non-relation members are ignored at import
  with a `STRAY_MEMBER` warning.
- **ImportRun**: One execution of the import against one snapshot.
  Records started/finished timestamps, per-entity counts, and overall
  outcome.
- **ImportAnomaly**: One recorded deviation. Carries severity
  (`fatal`/`warning`/`info`), a stable code, the affected entity
  reference, and the originating run.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Re-importing an unchanged snapshot completes with zero
  row changes (inserted = updated = deleted = 0 in the import report).
- **SC-002**: The full GCDA snapshot imports with at least 464 of 465
  masters servable and exactly the 1 known-unresolved master blocked,
  matching the validation report's verdict distribution.
- **SC-003**: 100% of stored transit records resolve through the full
  provenance chain to a recipe reference with no gaps.
- **SC-004**: 100% of recorded anomalies carry a severity and a stable
  code from the defined set; zero silent repairs (verified by review
  of the anomaly list against the validation report's known cases).
- **SC-005**: A full-snapshot import completes in under 30 minutes on
  a standard developer machine.
- **SC-006**: The import runs to success with all network interfaces
  disabled, proving offline operation.

## Assumptions

- The snapshot layout, filenames, and Overpass extraction queries in
  `data/osm/gcda/osm-extraction.md` are the frozen recipe v1; the
  spec's `recipe_ref` resolves to that document (its self-reference
  to a `docs/` path is reconciled at plan time to the actual file).
- The anomaly verdicts and counts in
  `data/osm/gcda/OSM_Validation_Report.md` describe the current
  snapshot and are the acceptance baseline for SC-002/SC-004.
- Small structural fixtures for the automated suite live under the
  samples directory (`data/osm/gcda/samples/`); plan decides the final
  test-fixture home.
- GCDA scope is fixed for this feature; additional regions are later
  features with their own snapshots.
- Timetable entities (`Trip`, `StopTime`, `ServiceCalendar`) remain
  unpopulated per constitution Principle VIII — this import covers
  geographic/transit structure only.
