# Quickstart: OSM Snapshot Import

**Feature**: [spec.md](spec.md) | **Date**: 2026-10-29

Validates the feature end to end. Uses the tracked sample fixtures for
the automated path; the full local snapshot for the manual path. No
implementation code below — commands and expected outcomes only.

## Prerequisites

- Backend scaffold working per `docs/setup-backend.md` (database up,
  migrations applied).
- Sample fixtures present in the transport app's test fixtures
  directory (copied from the retained samples at implement time).

## 1. Automated suite (sample snapshot)

Run the transport test suite. Expected: green, covering small-scale
import, idempotent rerun (zero changes), anomaly codes on fixture
data, and the provenance chain record → run → snapshot → recipe.

## 2. Manual import (full local snapshot)

Point the command at the retained snapshot directory and a scratch
report path. Expected: exit code 0, console summary with per-entity
counts, and a JSON report at the given path matching
[contracts/import-report.md](contracts/import-report.md).

## 3. Rerun idempotency

Run the identical command again. Expected: exit code 0 and a report
showing zero inserted/updated rows across all entities.

## 4. Anomaly review

Open the JSON report's `anomalies` list and the admin review screens.
Expected: every known deviation carries a severity and a stable code;
the blocked master is absent from servable data; quarantined and
orphan records are recorded but excluded; nothing was silently
repaired.

## 5. Provenance spot-check

Pick any stored stop and route. Expected: each resolves to one import
run, one snapshot row with all five mandated fields, and the recipe
reference.

## 6. Offline proof

With all network interfaces disabled, rerun the sample import.
Expected: success identical to the online run — the importer performs
no network I/O by construction.

## Done when

All six steps succeed, and review confirms the dataset contains
transit structure only (no timetable entities populated, per
constitution Principle VIII).
