# Implementation Plan: Ranked Journey Options

**Branch**: `010-ranked-options` | **Date**: 2026-10-31 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/010-ranked-options/spec.md` plus the requester plan-time slice (same agent + 008/009 tools; group verified pairs by `operator`; order by fewest stops then route id; boarding text from `resolved_origin` + `stop.name` only; destination list capped at 5 with evidence links; repair nudge and `_FORBIDDEN_SHAPED` unchanged; KSRTC/mixed/no-times tests).

## Summary

Single-answer journeys force unfamiliar passengers to guess. The fix ranks in `backend/apps/journey/agent.py` over `find_routes_matrix` output: group verified pairs by annotated `operator`, order by route stop count then route id, attach a boarding hint only from `resolved_origin` + `stop.name` (no stand table), and list up to 5 reachable destination members with evidence links. Verifier, repair nudge, and forbidden-content check run per option unchanged. Answer contract gains additive `option_groups`/`destinations`; prose still enumerates groups for old renderers. See [research.md](research.md) for decisions and rationale.

## Technical Context

**Language/Version**: Python 3.13, Django 5.2, DRF 3.18 (backend only; no frontend changes).

**Primary Dependencies**: 009 `find_routes_matrix`, 006 `resolved_origin`/`resolved_destination` annotations, master `operator` annotation (`routes_with_master_fields`). No new packages.

**Storage**: PostgreSQL 16 prod; SQLite-portable (no new queries beyond existing helpers); no migrations — ranking is per-request derivation.

**Testing**: Django test framework with stubbed model client; `python backend/manage.py test apps.journey apps.transport tests` (full-suite green gate). New ranked-answer tests: KSRTC-only wording, mixed-operator 2 groups, no-times text.

**Target Platform**: Existing single deployable (Django backend + PostgreSQL).

**Project Type**: Backend agent-policy slice in `backend/apps/journey/` (policy function + answer-shape extension + tests).

**Performance Goals**: Ranking runs over matrix pairs already fetched (no extra queries); destination cap of 5 bounds payloads for hub places.

**Constraints**: Read-only; no times/transfers/invented stands; `evidence` stays frontend `/routes/:id`; additive contract only; repair/`_FORBIDDEN_SHAPED` semantics unchanged.

**Scale/Scope**: MVP audience. One policy function in `agent.py`, additive answer fields, 3–5 tests, one contract doc.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I (MVP validation first)**: PASS — ranked options directly serve route/stop discovery for unfamiliar users.
- **II (Read-only public product)**: PASS — pure reads; no mutation surface.
- **III (No accounts, minimal data)**: PASS — per-request derivation; logs unchanged (meta only).
- **IV (Monorepo separation)**: PASS — backend-only; additive REST fields.
- **V (App-owned GTFS-inspired data + provenance)**: PASS — operator/endpoint annotations from canonical tables.
- **VI (Simple synchronous stack)**: PASS — no new infra or services.
- **VII (Django Admin operations)**: PASS — no admin/data-model change.
- **VIII (Schedule gates)**: PASS — no times/schedules; verifier still strips time-shaped content per option.
- **IX (Meta AI integration)**: PASS — model remains eloquence layer; ranking is deterministic code over verified pairs.

*Post-design re-check (Phase 1 complete): PASS — data-model adds no tables, contracts add no endpoints, quickstart introduces no runtime behaviour.*

## Project Structure

### Documentation (this feature)

```text
specs/010-ranked-options/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── answer.md        # option_groups/destinations shapes (additive to 004)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── apps/
│   └── journey/
│       ├── agent.py         # rank policy + answer shaping (verified pairs → groups)
│       └── tests/
│           └── test_ranked.py   # KSRTC/mixed/no-times tests (new file)
```

**Structure Decision**: Agent-policy slice reusing 008 selection context and 009 matrix; new test file keeps ranking tests separate; prose answer enumerates groups so current frontend rendering needs no change.

## Complexity Tracking

No constitution violations. No entries.

## Implementation notes (for /speckit-tasks)

1. `agent.py`: rank policy over matrix pairs — group by `route.operator` (`"Other services"` last when null/blank), order `(stop_count, route id)`; boarding hint from `resolved_origin` + `stop.name` only (absent otherwise); `destinations` first 5 reachable members with evidence; verifier + repair + `_FORBIDDEN_SHAPED` per option unchanged; prose enumerates groups.
2. Contract: apply `contracts/answer.md` additively to the `ok` shape (`option_groups`, `destinations`).
3. Tests in `backend/apps/journey/tests/test_ranked.py`: KSRTC-only matrix → KSRTC wording; mixed operators → 2 groups; answer text free of times/transfers; single-option → one-item list; deterministic repeat order.
