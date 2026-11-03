# Implementation Plan: API Abuse Protection

**Branch**: `015-api-abuse-protection` | **Date**: 2026-11-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/015-api-abuse-protection/spec.md` plus the requester's technical direction (Django + DRF `SimpleRateThrottle` with DB cache, no new deps; independent `journey_min` 60/min, `journey_day` 1500/day, `transcribe_min` 20/min, `transcribe_day` 300/day scopes with hashed IP identity, fully detached from shared read budgets; size/shape validation before throttle so oversized question 500 chars / history 10×500 / context 8KB returns 400 without burning budget; keep 5MB WAV checks; document DEBUG/ALLOWED_HOSTS and proxy env; update throttle and journey tests for independent budgets, order, and clamp behavior).

## Summary

Give the two expensive POST endpoints their own per-IP throttle budgets and a size envelope, both tunable via env. `journey` and `transcribe` leave the shared `transport_minute`/`transport_day` read budgets entirely and throttle under four new hashed-IP scopes. Shape and size validation runs before the budget check, so malformed or oversized requests get 400s without consuming budget or model quota; throttled requests get 429 + `Retry-After` without touching the model. See [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md).

## Technical Context

**Language/Version**: Python 3.13, Django + Django REST Framework (per `backend/requirements.txt`)

**Primary Dependencies**: No new dependencies — DRF `SimpleRateThrottle` subclasses and the existing DB-backed throttle cache (`transport_throttle_cache`, created with `manage.py createcachetable`)

**Storage**: No schema change; throttle counters reuse the existing cache table, keyed by scope + SHA-256(IP) — raw IPs never stored

**Testing**: Django test runner — extend `backend/apps/transport/tests/test_read_throttle.py` (independent budgets) and `backend/apps/journey/tests/` (order: 400-before-429, budget not consumed by rejections; preserve page clamp coverage)

**Target Platform**: Linux server; single deployable app (web + PostgreSQL)

**Project Type**: web-service (backend-only change; no frontend work)

**Performance Goals**: Throttle check stays a cache round-trip per request like today; size validation is pure-Python bounds on already-parsed JSON before any model call

**Constraints**: Endpoints stay login-free (no accounts, keys, captcha, WAF); plain-language errors only (429 throttled + `Retry-After`, 400 size); budgets: journey 60/min + 1500/day, transcribe 20/min + 300/day per client; caps: question 500 chars, history 10 turns × 500 chars, context 8KB serialized, audio 5MB WAV-only unchanged; everything env-overridable with safe compiled defaults

**Scale/Scope**: Two views (`journey`, `transcribe`), one throttling module, settings additions, tests; NAT-sharers share one budget by design (documented, not solved)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. MVP validation first** — PASS: abuse protection keeps the A-to-B answer service alive under flood; no product-surface change for legitimate passengers.
- **II. Read-only product** — PASS: budgets and caps only reject; no dataset mutation, no new feedback mechanics.
- **III. Open access / minimal data** — PASS: endpoints stay login-free (FR-008); identity stays a hashed IP, raw addresses never stored; filter-style minimal collection unchanged.
- **IV. Monorepo separation** — PASS: backend-only change; cross-boundary traffic stays on the versioned REST API with unchanged success shapes.
- **V. App-owned data + provenance** — PASS: reads existing stops/routes only; no data change.
- **VI. Simple synchronous stack** — PASS: DRF throttles + plain-Python bounds, no queue/service/worker, no new dependency.
- **VII. Admin as data interface** — N/A: no data-management change.
- **VIII. Schedule gating** — PASS: no times, durations, or frequencies involved.
- **IX. Meta AI integration** — PASS: model key stays server-side; throttle and size gates sit in front of the model and consume no quota on reject; evidence/refusal contract untouched.

*Re-check after Phase 1 design (2026-11-03): still PASS on all gates. No new dependency, service, migration, tracking, or privacy change; success payloads unchanged (only 429/400 rejection paths added around them).*

## Project Structure

### Documentation (this feature)

```text
specs/015-api-abuse-protection/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── throttle-budgets.md  # per-endpoint budgets, size caps, rejection shapes, env vars
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── config/
│   └── settings.py                  # DEFAULT_THROTTLE_RATES += 4 scopes; env-overridable budgets/caps; proxy/DEBUG docs
├── apps/
│   ├── transport/
│   │   ├── api/
│   │   │   └── throttling.py        # JourneyMinute/Day + TranscribeMinute/Day scopes (hashed IP); explicit check helper
│   │   └── tests/
│   │       └── test_read_throttle.py # extended: independence of new scopes from shared reads
│   └── journey/
│       ├── views.py                 # journey/transcribe: shape+size validate → budget check → logic (400 before 429)
│       └── tests/                   # order tests (oversized+over-budget → 400, budget unconsumed); keep page-clamp coverage
```

**Structure Decision**: Backend-only web-service change. Throttle scopes live with the existing throttling module; enforcement order lives in the two journey views; rates/caps live in settings behind env. No frontend, migration, or service changes.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations — table not needed.
