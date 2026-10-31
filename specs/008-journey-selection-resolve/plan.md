# Implementation Plan: Journey Selection Resolve

**Branch**: `008-journey-selection-resolve` | **Date**: 2026-10-31 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/008-journey-selection-resolve/spec.md` plus the requester plan-time stack/behaviour decisions (Django 5.2 + DRF, OpenAI SDK server-side for `muse-spark-1.3`, React Vite frontend, Postgres with SQLite-portable tests, existing 003 plus 006 queryset helpers).

## Summary

Passengers who pick a stop from a candidate list get stuck in a repeat prompt. The fix adds a deterministic selection fast-path in `backend/apps/journey/agent.py`: `_resolve_selection(context, question_text)` validates IDs/slot and returns `(from_id, to_id)` — the click path uses the sent `selected_stop_id`, the typed path derives it by unambiguous text match (exact name or 1-based position matching exactly one candidate). `run_journey` calls `tools.find_routes` directly and `_verify_route`s each result, returning `_answer_payload` or a `_NO_DIRECT` refusal without ever calling the model. Both-ends ambiguity returns `slots{from_ids,to_ids}` plus `surviving_context{other_end_ids}` instead of `(None, None)`, and every `disambiguate` response carries `slot`/`offered_ids` plus per-candidate `detail` (`name_ml` or rounded coordinates). The contract change to `specs/004-journey-agent/contracts/journey.md` is additive only; `views.py` stays pass-through. `frontend/src/components/JourneyPanel.jsx` sends full IDs/slot/context and preserves history. See [research.md](research.md) for decisions and rationale.

## Technical Context

**Language/Version**: Python 3.13, Django 5.2, DRF 3.18 (backend); React + JSX (per constitution v1.4.0) + Vite + Vitest (frontend).

**Primary Dependencies**: OpenAI SDK (Python, server-side only) for `muse-spark-1.3` (code default `JOURNEY_MODEL`; env governs); existing 003 read helpers (`servable_routes`, `order_routes`, `routes_with_master_fields`) plus 006 endpoint annotations. No new packages.

**Storage**: PostgreSQL 16 prod via existing `postgresql` backend; SQLite-portable SQL in tests; no migrations — selection state is transient request/response context, server stores nothing.

**Testing**: Django test framework with stubbed model client (no network); `python backend/manage.py test apps.journey apps.transport tests` (125 OK gate); `npm test -- --run` (53 passed gate). New backend `SelectionTests` (both-ends-ambiguous fixture, forged ID, missing `resolved`) plus frontend payload test (IDs + slot + surviving context).

**Target Platform**: Existing single deployable (Django backend + PostgreSQL); responsive web frontend.

**Project Type**: Full-stack monorepo fix: backend agent fast-path + additive contract + frontend panel payload fix.

**Performance Goals**: Selection path makes zero model calls — latency is DB lookups only (`find_routes` + per-route `_verify_route`); no extra queries beyond the existing verified-answer shape.

**Constraints**: Tools stay read-only MCP-compatible (no MCP server); no times/transfers/invented content (server verifier); additive contract only; `views.py` pass-through; `meta: model none / provider local-fallback / resolution selection` on the selection path (outage fallback carries no `resolution` key); `tools_used` audit records the direct `find_routes` call via manual tracker bookkeeping; no PII in logs (model/provider/latency/tools only).

**Scale/Scope**: MVP audience. One agent module (~400 lines, +~60-line fast-path), one panel component (`choose`/`ask`), one contract delta, 4–6 backend tests + 1–2 frontend tests.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I (MVP validation first)**: PASS — fixes the core "how do I get from A to B" flow for unfamiliar users, the primary audience.
- **II (Read-only public product)**: PASS — selection uses direct `find_routes` reads only; no mutation surface.
- **III (No accounts, minimal data)**: PASS — stateless per-request context; no login/tracking; logs carry meta only, no PII.
- **IV (Monorepo separation)**: PASS — frontend talks only via versioned REST; `views.py` unchanged except pass-through.
- **V (App-owned GTFS-inspired data + provenance)**: PASS — reads canonical tables via 003 helpers; no live OSM; provenance untouched.
- **VI (Simple synchronous stack)**: PASS — no new infra, queues, routers, or MCP server.
- **VII (Django Admin operations)**: PASS — no admin/data-model change.
- **VIII (Schedule gates)**: PASS — no times/schedules introduced; verifier still strips time/transfer shapes.
- **IX (Meta AI integration)**: PASS — model called server-side only; tools are pure read-only JSON-schema functions, MCP-compatible; answers evidence-linked at `/routes/:id`, refuse-when-unknown, disambiguate-when-ambiguous; every response exposes model/provider/latency and renders AI-labelled unverified; voice remains input-mode only.

*Post-design re-check (Phase 1 complete): PASS — data-model adds no tables, contracts are additive, quickstart introduces no new runtime behaviour.*

## Project Structure

### Documentation (this feature)

```text
specs/008-journey-selection-resolve/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── selection.md     # Additive delta to 004 journey.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── apps/
│   ├── journey/
│   │   ├── agent.py         # _resolve_selection + fast-path + both-ends slots
│   │   ├── tools.py         # unchanged (find_routes/search_stops/get_route_detail)
│   │   ├── views.py         # pass-through only (unchanged logic)
│   │   └── tests/
│   │       └── test_journey.py  # + SelectionTests
├── config/
│   └── settings.py      # JOURNEY_MODEL / JOURNEY_MODEL_PROVIDER (unchanged)
└── manage.py

frontend/
├── src/
│   ├── api/
│   │   └── journey.js       # postJourney (unchanged shape)
│   └── components/
│       ├── JourneyPanel.jsx       # choose/ask payload fix
│       └── JourneyPanel.test.jsx  # + payload test
└── package.json
```

**Structure Decision**: Full-stack fix inside the existing monorepo layout. Backend owns all resolution/verification; frontend change is payload-only with an unchanged render path; contract delta lives in the feature dir and is applied additively to `specs/004-journey-agent/contracts/journey.md` at implementation time.

## Complexity Tracking

No constitution violations. No entries.

## Implementation notes (for /speckit-tasks)

1. `agent.py`: add `_resolve_selection(context, question_text)` (`selected_stop_id` int non-bool + member of `candidate_stop_ids`, `slot` in `{from,to}`, `resolved.id` int; when `selected_stop_id` is absent derive it by unambiguous text match of `question_text` against offered candidates — case-insensitive exact name or 1-based position/ordinal matching exactly one entry, else `None`) → `(from_id, to_id)` or `None`; fast-path at top of `run_journey` before model loop (direct `tools.find_routes`, manual `tracker["tools_used"].append("find_routes")` plus `calls`/`findings` bookkeeping, `_verify_route` each, `_answer_payload` or `_NO_DIRECT` refuse, `meta none / local-fallback / resolution selection`, never call the model); disambiguation helper (new; no existing `_disambiguation_context` in code) emits `slot`/`offered_ids`/`resolved` and per-candidate `detail` on every prompt and `slots{from_ids,to_ids}` + `surviving_context{other_end_ids}` for both-ends.
2. Contract: apply `contracts/selection.md` additively to `specs/004-journey-agent/contracts/journey.md` (`disambiguate{slot, resolved:{id,name}, offered_ids}`, per-candidate `detail`, selection reply `{question, history[original], context{...}}`, `meta{resolution:selection}`).
3. `JourneyPanel.jsx`: `choose(candidate, payload)` sends full payload + IDs/slot/resolved; `ask()` preserves original question (stop forcing `history: []`).
4. Tests: backend `SelectionTests` (both-ends fixture, forged ID, missing `resolved`); frontend payload test; regression `manage.py test apps.journey apps.transport tests` 125 OK + `npm test -- --run` 53 passed.
