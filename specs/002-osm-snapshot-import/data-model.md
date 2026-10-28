# Data Model: OSM Snapshot Import

**Feature**: [spec.md](spec.md) | **Date**: 2026-10-29

Eight entities. Natural identity everywhere is (`osm_type`, `osm_id`);
surrogate keys exist only where the ORM needs them. All rows carry the
run that created them; the run carries the snapshot; the snapshot
carries the recipe reference.

## OsmSnapshot

One retained extract batch. Append-only: a changed file set is a new
row, never an edit.

- `label` (text, required): human name, defaults to the snapshot
  directory's base name.
- `recipe_ref` (text, required): repo-relative path of the frozen
  extraction recipe document.
- `source_timestamps` (JSON, required): per-file OSM base timestamps
  as stated in the snapshot files; recorded only when present, never
  fabricated. Absent timestamps are recorded as absent, not defaulted.
- `retrieved_at` (timestamptz, required): when the extract was fetched.
- `imported_at` (timestamptz, required): when this snapshot was
  imported (set by the run).
- Validation: all five fields present (constitution V); (`label`)
  unique per series.
- State transitions: created once per snapshot; immutable afterwards.

## Stop

A bus stop platform: an OSM `node` tagged `highway=bus_stop`.

- Natural key: (`node`, OSM id). Attributes: `name` (nullable —
  unnamed stops exist), `name_ml` (nullable), `lat`/`lon` (required
  floats), `tags` (JSON object of remaining amenity tags).
- Index: composite B-tree on (`lat`, `lon`).
- Validation: coordinates required; a stop changing coordinates
  between snapshots updates in place (same natural key).

## RouteMaster

A `route_master` relation grouping direction variants.

- Natural key: (`relation`, OSM id). Attributes: `name`, `operator`
  (nullable), `network` (nullable), `verdict`, warning flags (list).
- Validation: identity is the OSM ID — duplicate names across masters
  are kept as separate rows with a `DUPLICATE_MASTER_NAME` warning,
  never merged.
- Verdict values: `VALID`, `VALID_WITH_WARNING`, `MISSING_DATA`,
  `AMBIGUOUS`, `UNRESOLVED`.

## Route

A `route` relation: one direction or variant, belonging to one master.

- Natural key: (`relation`, OSM id). Attributes: `name`, `from_text`,
  `to_text`, `direction` (nullable — null when from equals to or the
  pair is asymmetric, with a warning), `verdict`, `quarantined`
  (platform-less routes are flagged and kept out of served data;
  quarantine is a stored flag, never a silent fix).
- Relationship: many-to-one to `RouteMaster` via `RouteMasterMembership`
  (a route belongs to exactly one master in the master-driven import;
  master-less routes are tracked as orphans, not served).

## RouteStopMembership

Ordered platform membership of a route.

- Composite identity: (`route`, `position`). Attributes: `stop`
  reference, `position` (1-based, contiguous within the route),
  `source_index` (original member index in the OSM relation).
- Validation: positions form an unbroken 1..N sequence per route;
  only `role=platform` node members participate — road-geometry members
  are excluded from stop ordering. Duplicate platforms keep original
  order with a `DUPLICATE_PLATFORM` warning; never deduped.
- Rebuild rule: memberships are derived state — each import rebuilds
  them per parent inside the run's transaction.

## RouteMasterMembership

Child-route membership of a master, preserving source order.

- Composite identity: (`route_master`, `position`). Attributes:
  `route` reference, `position`, `source_index`.
- Validation: only `relation`-type members participate;
  non-relation members are ignored with a `STRAY_MEMBER` warning. A
  child reference absent from the snapshot is fatal for the master
  (`CHILD_REF_MISSING`) — the master is blocked, not partially built.

## ImportRun

One execution of the import against one snapshot.

- Attributes: snapshot reference, `started_at`, `finished_at`,
  `outcome` (`succeeded` / `aborted`), per-entity inserted / updated /
  unchanged counts.
- State transitions: `running` → `succeeded` (report written, even
  with warnings) or `aborted` (fatal file-level failure; transaction
  rolled back, nothing served from this run).
- Validation: exactly one snapshot per run; counts reconcile with the
  report file.

## ImportAnomaly

One recorded deviation. Immutable once written.

- Attributes: severity (`fatal` / `warning` / `info`), stable `code`,
  affected entity reference (nullable for file-level anomalies),
  originating run reference, detail text.
- Validation: every row carries a severity and a code from the closed
  set; free text explains, never substitutes for, the code.
- Cardinal rule: anomalies are recorded, quarantined, or blocking —
  never auto-repaired. Code that alters source data to "fix" an
  anomaly violates this model.
