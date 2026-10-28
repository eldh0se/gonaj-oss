# Contract: `import_osm_snapshot` CLI

**Feature**: [spec.md](../spec.md) | **Date**: 2026-10-29

The sole entry point of this feature. No HTTP, no UI.

## Synopsis

```text
manage.py import_osm_snapshot --snapshot-dir DIR
    [--report-path PATH] [--snapshot-label LABEL]
```

## Flags

| Flag | Required | Default | Meaning |
|------|----------|---------|---------|
| `--snapshot-dir` | yes | — | Retained snapshot directory holding the input files |
| `--report-path` | no | `./osm-import-report.json` | Where the machine-readable report is written |
| `--snapshot-label` | no | base name of `--snapshot-dir` | Human name recorded on the snapshot row |

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Run completed and the report was written — including runs with warnings, blocked masters, or quarantined records. Data outcomes are in the report, not the exit code. |
| `1` | Run aborted before any write: missing/unparsable required file, intra-file duplicate OSM ID. The transaction rolled back; no partial dataset exists from this run. A fatal anomaly is still recorded where a run row exists. |

## Console output

On completion, one human-readable summary line group is printed:
per-entity inserted/updated/unchanged counts, anomaly totals by
severity, and the report file path. Full detail lives in the JSON
report ([import-report.md](import-report.md)), never only on the
console.

## Non-goals (explicitly out of contract)

- No `--watch`, `--daemon`, or scheduling flags: one shot per
  invocation; repetition is the operator's or OS scheduler's job.
- No network flags or credentials: the command performs no network
  I/O, so there is nothing to configure.
- No `--force`/`--repair` flags: silent repair is forbidden, so no
  flag may enable it.
