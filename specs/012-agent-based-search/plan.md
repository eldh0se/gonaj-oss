# Implementation Plan: Agent-Based Area Search for Direct Journeys

**Branch**: `012-agent-based-search` | **Date**: 2026-11-01 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/012-agent-based-search/spec.md`

## Summary

Route every journey answer through groups-first search (`search_places` →
`find_routes_matrix` → `get_route_detail`), classifying each viable route as
an exact served stop plus walkable mates (`d <= 150m` via new `distance_m`),
answering per route with `/routes/:id` evidence and a walk note, and offering
the map/list pick only when pairs went untested or the place never matched.
Adds `distance_m` + `nearby_stops` tools (`nearby_stops` created now,
consumption deferred to the next feature), promotes two existing tools to the
model, replaces the single-pair entry flow (FR-011) — `answer_direct` stays
as leaf verifier and is removed only as an entry answer (research Decision 6,
preserving 011's exact-stop tap semantics) — and applies the three
clarify outcomes (refuse-vs-pick C, member-distance nearness B, ≤5 cited
destinations B). Backend-only; no migration, no new service, no endpoint
change; FR-001 forbids live location overriding a named end. See
[research.md](./research.md) for all planning-time decisions,
[data-model.md](./data-model.md) for structures, [contracts/](./contracts/)
for tool/answer shapes, [quickstart.md](./quickstart.md) for validation.

## Technical Context

**Language/Version**: Python 3.13, Django + Django REST Framework (per `backend/requirements.txt`)

**Primary Dependencies**: Existing 003 transport query helpers
(`servable_routes`, `routes_with_master_fields`,
`routes_with_endpoint_names`, `order_routes`); Meta backend SDK via
`apps.journey.providers.meta` (declared model calls only, stubbed in tests)

**Storage**: PostgreSQL + PostGIS in production; all new code SQLite-portable
(pure-Python haversine via existing `_haversine_m`, DB bbox prefilters — no
PostGIS functions), so journey unit tests run without a live database

**Testing**: Django test runner — `python manage.py test apps.journey`;
factories (`apps.transport.tests.factories`) + stubbed provider convention
per `test_journey.py`

**Target Platform**: Linux server; single deployable app (web + PostgreSQL)

**Project Type**: web-service (monorepo; this feature touches `backend/` only,
`frontend/` unchanged)

**Performance Goals**: Pair test bounded at 200 pairs nearest-first (each
empty pair = 1 indexed query); `search_places` pre-grouping cap 100/side
unchanged; `nearby_stops` ≤100 rows; inexact intent-check retries bounded at
3 attempts per end with `exclude_ids`; no separate latency target — bounded
work instead

**Constraints**: Read-only tools (never raise; `{"ok": False, ...}` on bad
input); no new services, queues, or routing engines; response `meta`
(model, provider, latency) and `tools_used` audit logging preserved via
`execute_tool`/`_direct_tool`; name search is two-stage (`exact` True on
`icontains` hit, `exact` False plus token scores on overlap fallback ranked
by shared count desc, exact-phrase bonus, fewer extra tokens, name, id);
inexact ends go to a same-place model allowlist (`KEEP <ids>` for same-place
members only; only listed ids are kept and the rest are dropped; a bare
`ACCEPT` keeps nothing unless ids are listed) with dropped members retried
via `exclude_ids`; `MAX_TOOL_TURNS` (4), `pos_from < pos_to` verifier,
200-pair cap, 5-destination cap, and FR-011 no-bypass stay unchanged

**Scale/Scope**: ≤100 stops per `search_places` side → ≤200 tested pairs;
≤5 destinations cited; ≤3 walk-note mates per end + overflow count

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. MVP validation first** — PASS: directly answers "How do I get from A
  to B" for direct services; the exact defect (wrong-side refusal) is the
  MVP's core journey question.
- **II. Read-only product** — PASS: tools read canonical tables only; no
  dataset mutation, no admin changes, no crowdsourcing mechanics.
- **III. No accounts / minimal data** — PASS: no identity, no tracking; only
  existing aggregate log signals (`tools_used` list already logged).
- **IV. Monorepo separation** — PASS: `backend/apps/journey/` only; no API
  shape change (agent envelope unchanged); frontend untouched.
- **V. App-owned GTFS-inspired data + provenance** — PASS: reads Stop /
  Route / RouteStopMembership via existing helpers; no OSM-live queries.
- **VI. Simple synchronous stack** — PASS: plain Python + Django ORM;
  haversine in Python, not a routing engine; no Kafka/Redis/Celery/K8s.
- **VII. Admin as data interface** — N/A: no data-management change.
- **VIII. Schedule gating** — PASS: no times/durations/frequencies; the
  verifier (`_FORBIDDEN_SHAPED` + repair retry) still rejects them.
- **IX. Meta AI integration** — PASS: declared SDK only; tools stay
  read-only with JSON schemas, MCP-compatible, no MCP server; answers stay
  evidence-grounded with refuse-on-unknown, `/routes/:id` citations, and
  model/provider/latency meta.

*Re-check after Phase 1 design (2026-11-01): still PASS on all gates. Design
adds no dependency, no service, no migration, no endpoint, no tracking; the
only new code is two read-only tools and agent-flow rewiring inside the
existing module.*

## Project Structure

### Documentation (this feature)

```text
specs/012-agent-based-search/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   ├── tool-schemas.md  # promoted + new tool JSON schemas, validator rules
│   └── answer-shape.md   # per-route block, prose template, fallback selection
├── dev-notes/           # input design docs (loop, tools, instructions)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── apps/
│   └── journey/
│       ├── tools.py     # promote search_places + find_routes_matrix; add distance_m + nearby_stops
│       ├── agent.py     # SYSTEM_PROMPT, entry-flow replacement (FR-011), validators, ranking/answer prose
│       └── tests/       # Django tests: tools, matrix flow, no-bypass, fallback selection, audit
```

**Structure Decision**: Web-application monorepo, backend-only change. The
frontend is untouched (no new endpoint, no payload-shape break — the answer
payload gains additive `also_nearby*`/`overflow_nearby` fields inside the
existing option objects). No migration: zero schema change.

## Complexity Tracking

> No constitution violations — table intentionally empty.
