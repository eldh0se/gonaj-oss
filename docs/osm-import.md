# OSM Snapshot Import — operator runbook

Bulk-loads the retained Greater Cochin transit snapshot into the
application database. Part of `specs/002-osm-snapshot-import`.

## When to run this

- First population of a fresh database.
- A new snapshot batch arrives (changed source files).
- Re-verification after fixing source data upstream.

Day-to-day curation happens in Django Admin, not here.

## Prerequisites

- Backend scaffold working per `docs/setup-backend.md`
  (database up, migrations applied — including the transport tables).
- A snapshot directory holding the input files (untracked by git;
  see the layout below). Never edit files in place.

Expected layout:

```text
<snapshot-dir>/
  osm_gcda_routes.json         # required
  osm_gcda_bus_stops.json      # required
  osm_gcda_route_masters.json  # required
  osm_gcda_bus_stations.json   # optional
  osm_gcda_route_members.json  # optional
```

## Run it

From the repository root with the project environment active:

```sh
cd backend
./manage.py import_osm_snapshot \
  --snapshot-dir ../data/osm/gcda \
  --report-path /tmp/osm-import-report.json \
  --snapshot-label gcda
```

Flags: `--snapshot-dir` selects the input; `--report-path` selects
where the machine-readable report lands (default
`./osm-import-report.json`); `--snapshot-label` names the snapshot
(default: the directory's base name).

## Read the result

The console prints per-entity inserted/updated/unchanged counts plus
anomaly totals by severity. The JSON report holds the full detail:
snapshot identity and timestamps, per-entity counts, and every anomaly
with severity and stable code.

What the numbers mean:

- **Rerun shows all zeros** — the snapshot is unchanged; nothing was
  written. This is the expected steady state.
- **Warnings** (`DUPLICATE_PLATFORM`, `STRAY_MEMBER`,
  `ASYMMETRIC_FROM_TO`, `ORPHAN_ROUTE`, `DUPLICATE_MASTER_NAME`,
  `NO_PLATFORM_SEQUENCE`) — data imported with flags. Review in
  Admin; fix upstream in OSM, never by hand-editing rows.
- **Fatal `CHILD_REF_MISSING`** — a master references a missing
  child; the master is blocked until the source extract is fixed.
- **Exit code 1** — the run aborted before any write (missing or
  invalid required file, duplicate IDs inside one file). Nothing was
  partially saved; the report names the fatal anomaly.

## Reruns and new snapshots

- Same files, same label → the existing snapshot row is reused and
  the rerun reports zero changes.
- Changed files, same label → recorded as a new snapshot row plus a
  new run. History appends; nothing is overwritten or deleted.
- There is no `--force` or `--repair` flag, by design: the import
  never silently fixes source data.

## Troubleshooting

- **Database unreachable** — start it first (`docker compose up -d db`
  from the repo root) and confirm the `POSTGRES_*` settings.
- **Missing SECRET_KEY** — export it; the settings fail fast naming
  the variable.
- **Blocked masters after a fresh extract** — compare the report's
  fatal anomalies against the previous run before investigating;
  single-master blocks usually mean an incomplete extract, so
  re-fetch before touching anything else.
