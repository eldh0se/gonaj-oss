# Implementation Plan: Debug and Production Logging

**Branch**: `007-debug-production-logging` | **Date**: 2026-10-31 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/007-debug-production-logging/spec.md`

## Summary

Backend logging today is Django defaults plus ad-hoc
`getLogger(__name__)` calls in the journey code; transport
views, the exception handler, and the import command emit
nothing, and the frontend has no logging. This plan adds a
mode-dependent `LOGGING` dict in `backend/config/settings.py`
(`DEBUG` threshold in debug mode, `INFO` in production,
console streams only), error-boundary log records at the
transport 5xx path and import outcome (reusing the journey
`logger.info`/`logger.exception` precedent, with the same
never-log rules for keys, questions, answers, transcripts,
and audio), and a `import.meta.env.DEV`-gated debug helper in
the frontend API layer. No models, migrations, dependencies,
or services. See [research.md](research.md) for decisions
and rationale.

## Technical Context

**Language/Version**: Python 3.13, Django 5.2 + DRF
(backend, unchanged); JavaScript, React 18 + Vite 6
(frontend, unchanged).

**Primary Dependencies** (none new): Python stdlib
`logging` via the Django `LOGGING` setting; Vite built-in
`import.meta.env.DEV` on the frontend. No new packages.

**Storage**: N/A — no schema change. Log output goes to
captured process streams; retention/rotation stays with the
deployment environment per the spec assumption.

**Testing**: Backend Django test suite (`backend/` tests,
`assertLogs`-style capture for thresholds, error entries,
and redaction); frontend Vitest suite (console spy +
`import.meta.env.DEV` gating).

**Target Platform**: Same deployable (web app +
PostgreSQL/PostGIS); portable behaviour under
`DJANGO_DEBUG=1/0`.

**Project Type**: Cross-cutting observability change in the
monorepo (`backend/` primarily, one small `frontend/`
helper).

**Performance Goals**: Negligible overhead — no per-request
logging on routine success paths in production; no
additional queries from logging call sites.

**Constraints**: API response bodies and plain-language
error wording unchanged (no internals in responses);
`MODEL_API_KEY`/secrets/questions/answers/transcripts/audio
never in logs (constitution IX); no user tracking beyond
permitted aggregates (constitution III); no new services or
infrastructure (constitution VI).

**Scale/Scope**: MVP audience. One settings block, log
records at three boundary sites (transport errors, import
outcome, existing journey calls kept), one frontend helper,
tests on both sides.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I (MVP validation first)**: PASS — faster diagnosis and
  production triage directly serve the validation question
  by keeping route/stop discovery issues debuggable.
- **II (read-only public product)**: PASS — logging adds no
  writes, no data-entry surface, no feedback changes.
- **III (no accounts, minimal data)**: PASS — FR-007, the
  redaction rule, and never-log rules prohibit tracking and
  personal data in logs; verified by SC-004 sweep.
- **IV (monorepo separation)**: PASS — backend change in
  `backend/`, frontend helper in `frontend/`, communicating
  only over the existing versioned REST API.
- **V (app-owned data + provenance)**: PASS — no stored
  data, no import-format change, provenance untouched.
- **VI (simple stack, deferred complexity)**: PASS — stdlib
  logging + a settings dict; no services, queues, files,
  aggregators, or packages.
- **VII (Django Admin)**: PASS — no data operations.
- **VIII (schedule gating)**: PASS — no times or schedules.
- **IX (Meta AI)**: PASS — keeps the existing journey rule
  (model/provider/latency/tools only) and extends the same
  never-log discipline to all new call sites; key stays out
  of logs.

Post-design re-check: no new violations introduced by
[research.md](research.md), [data-model.md](data-model.md),
[contracts/logging.md](contracts/logging.md), or
[quickstart.md](quickstart.md). No Complexity Tracking
entries required.

## Project Structure

### Documentation (this feature)

```text
specs/007-debug-production-logging/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── logging.md       # Log record contract (format, levels, redaction)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── config/
│   └── settings.py          # LOGGING dict (mode-dependent threshold, console handler)
├── apps/
│   ├── transport/api/       # error-boundary records (5xx + traceback, 4xx restrained)
│   ├── transport/           # import command outcome records
│   └── journey/             # existing records kept under shared rules
└── tests/ + apps/*/tests/   # threshold, entry, and redaction tests

frontend/
├── src/
│   └── api/                 # DEV-gated debug helper
└── src/api/*.test.js, components/*.test.jsx  # gating tests (Vitest)
```

**Structure Decision**: Web application layout (existing
`backend/` Django + `frontend/` React monorepo, unchanged).
Backend carries the primary surface (settings + three
boundary sites); frontend gets one build-gated helper in
the API layer module that already owns all API calls.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

None — no violations.
