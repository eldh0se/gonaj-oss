# Research: OSM Snapshot Import

**Feature**: [spec.md](spec.md) | **Date**: 2026-10-29

The user input pinned the implementation shape (management command,
single transaction, order-preserving parse, JSON + console reporting),
so no NEEDS CLARIFICATION remained. Each decision below records what
was chosen, why, and what was set aside.

## Decision: Command interface with three flags

- **Decision**: `import_osm_snapshot --snapshot-dir DIR [--report-path
  PATH] [--snapshot-label LABEL]`. `--snapshot-dir` is required;
  `--report-path` defaults to `./osm-import-report.json`;
  `--snapshot-label` defaults to the snapshot directory's base name.
- **Rationale**: The directory flag selects input; the report flag
  selects the machine-readable output; the label names the snapshot
  for human review and repeat runs. Defaults make the common case a
  one-flag invocation while keeping every run explicitly addressable.
- **Alternatives considered**: Mandatory label (rejected — the
  directory name is a natural, stable default); report to stdout only
  (rejected — CI and review need a retained artifact file).

## Decision: Parse-then-write inside one transaction

- **Decision**: Parse all snapshot files into memory, evaluate policy,
  then write everything inside a single database transaction. Any
  aborting failure rolls back to zero partial state.
- **Rationale**: Guarantees the spec's no-partial-dataset rule with
  the simplest possible mechanism. The full snapshot (~30 MB JSON) fits
  comfortably in memory, and cross-file joins (platforms → stops,
  children → masters) plus order preservation require the full picture
  before writing.
- **Alternatives considered**: Streaming/chunked commits (rejected —
  breaks atomicity and complicates the zero-change rerun accounting);
  staging tables (rejected — a second schema for no additional safety).

## Decision: Upsert with change detection

- **Decision**: Natural-key lookup on (`osm_type`, `osm_id`), then save
  only when a field differs, counting inserted / updated / unchanged
  per entity for the report. Re-running an unchanged snapshot performs
  zero writes.
- **Rationale**: Makes the idempotency requirement directly observable
  in the report instead of merely asserted.
- **Alternatives considered**: Blind `update_or_create` (rejected —
  touches rows and `updated` counts even when nothing changed);
  delete-and-reload per snapshot (rejected — destroys history and
  breaks the append-only snapshot model).

## Decision: Membership rebuild per parent inside the transaction

- **Decision**: For each imported route/master, delete its existing
  memberships and bulk-recreate them with recomputed contiguous
  `position` values, preserving each member's original `source_index`.
- **Rationale**: Membership order is derived state, not independent
  data; rebuild keeps `position` contiguous by construction even when
  source relations change shape between snapshots.
- **Alternatives considered**: Positional diffing (rejected — complex
  for no benefit, since rebuild inside a transaction is atomic and the
  row counts are small per parent).

## Decision: Composite B-tree index on stop coordinates

- **Decision**: B-tree index on `Stop(lat, lon)`; no spatial index and
  no GeoDjango field use in this feature.
- **Rationale**: Satisfies the near-stop lookup need the plan states
  with the plain backend already in use. Spatial indexes arrive with
  the spatial feature that justifies the PostGIS dependency.
- **Alternatives considered**: GiST/PostGIS now (rejected — adds the
  native GIS dependency chain before any spatial query exists).

## Decision: Transport app colocated with its tests and fixtures

- **Decision**: New `backend/apps/transport/` app holding models,
  importer package, management command, admin registration, and its
  own `tests/` package with `fixtures/osm/` sample copies.
- **Rationale**: Follows the `backend/apps/` convention the scaffold
  plan established; keeps the domain, its policy engine, and its
  proof together. Cross-cutting tests stay in `backend/tests/`.
- **Alternatives considered**: Top-level `transport/` package
  (rejected — breaks the monorepo's `backend/apps/` layout);
  fixtures only in `backend/tests/` (rejected — splits the domain's
  proof from the domain).

## Decision: Recipe reference is the repo-relative recipe path

- **Decision**: `recipe_ref` records the repo-relative path of the
  frozen extraction recipe document for the snapshot series.
- **Rationale**: Unambiguous, stable across machines, and directly
  openable from a checkout — exactly what future evidence processing
  needs to reproduce the snapshot's origin.
- **Alternatives considered**: Free-text recipe names (rejected —
  unresolvable); URLs (rejected — rot over time, and the recipe is
  versioned in-repo).

## Decision: Fixed anomaly code set with verdict mapping

- **Decision**: Closed code set (`CHILD_REF_MISSING`,
  `NO_PLATFORM_SEQUENCE`, `DUPLICATE_PLATFORM`, `STRAY_MEMBER`,
  `ASYMMETRIC_FROM_TO`, `ORPHAN_ROUTE`, `OPTIONAL_FILE_MISSING`,
  `DUPLICATE_MASTER_NAME`, plus file-level `REQUIRED_FILE_MISSING`,
  `INVALID_JSON`, `DUPLICATE_OSM_ID`) each bound to one severity and
  one disposition (block run / block record / quarantine / flag /
  note).
- **Rationale**: Stable codes make anomalies queryable, countable in
  the report, and comparable across runs — the mechanism that turns
  "no silent repair" from a slogan into verifiable behavior.
- **Alternatives considered**: Free-text messages only (rejected —
  unqueryable); severity without codes (rejected — cannot track
  recurrence of the same defect class).

## Decision: Offline by construction, not by discipline

- **Decision**: The importer package performs no socket I/O as a
  structural property (no networking imports), verified by running
  the suite with network interfaces disabled.
- **Rationale**: A rule that depends on operators remembering is
  weaker than code that cannot phone home. The offline proof in the
  success criteria tests the structure, not anyone's memory.
- **Alternatives considered**: Documented "do not add network calls"
  convention (rejected — unenforceable).

## Decision: JSON report file plus console summary

- **Decision**: Every run writes the full machine-readable report to
  `--report-path` (schema in `contracts/import-report.md`) and prints
  a short human summary to the console (counts + anomaly totals by
  severity). Formats are defined in `contracts/`.
- **Rationale**: Two audiences — automation and the operator watching
  the run. The file is the artifact CI and review keep; the console
  line is the at-a-glance verdict.
- **Alternatives considered**: Console only (rejected — nothing to
  retain or diff); JSON only (rejected — poor operator experience).
