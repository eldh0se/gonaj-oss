# Implementation Plan: Journey Agent

**Branch**: `004-journey-agent` | **Date**: 2026-10-29 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/004-journey-agent/spec.md`, plus the requester's plan-time stack decisions (model, SDK, tools, voice, auth, session, verifiability) and reference docs (`https://dev.meta.ai/docs/*`).

## Summary

A passenger journey helper: the passenger asks in plain words
(typed or spoken) how to get from A to B; the backend runs a
declared Meta model (`muse-spark-1.3`) in a tool loop over three
read-only tools (`search_stops`, `find_routes`,
`get_route_detail`); a server-side verifier admits only
evidence-verified direct connections (both stops in order, no
times or transfers) and otherwise refuses or asks the passenger
to disambiguate. Voice input goes through Muse Voice Transcribe
as an input mode with an editable transcript and no audio
retention. Every response carries model, provider, and latency in
its meta and logs, and renders distinctly labelled unverified.
See [research.md](research.md) for decisions and rationale.

## Technical Context

**Language/Version**: Python 3.13, Django 5.2, DRF 3.18 (backend,
as in 001–003); React + TypeScript, Leaflet map (frontend,
unchanged stack).

**Primary Dependencies**: OpenAI SDK (Python, server-side only)
pointed at `https://api.meta.ai/v1`; declared models
`muse-spark-1.3` (tool loop) and `muse-voice-transcribe-1.0`
(PUSH_TO_TALK transcription). No new Python or npm packages
beyond the OpenAI SDK.

**Storage**: PostgreSQL 16 via the existing plain `postgresql`
backend. No new tables and no migrations: the agent is stateless
per request, tools read the canonical tables imported by 002 via
the shared 003 query helpers, and transcripts/audio are never
stored.

**Testing**: Django test framework with a stubbed model client
(no network in tests); DRF test client for the journey and
transcribe endpoints; frontend component tests for transcript
editing and unverified labelling.

**Target Platform**: The existing single deployable application
(Django backend + PostgreSQL); consumers are the passenger
frontend chat panel and any reviewer inspecting logs.

**Project Type**: Full-stack feature in the monorepo: new
`backend/apps/journey/` domain app behind the versioned
`/api/v1/` REST boundary, plus a frontend chat/voice panel
consuming only that boundary.

**Performance Goals**: Journey answers complete within a short
model timeout (20 s, one retry, then the non-AI fallback) so the
chat stays responsive; tool queries reuse the single-query-shaped
reads from 003.

**Constraints**: Read-only tools (GET-equivalent ORM reads only);
no schedules, times, transfers, or invented content may reach the
passenger (server-side verifier strips or refuses); no audio
retention anywhere; no accounts, tracking, or per-user memory;
`MODEL_API_KEY` server-side only, never exposed to the frontend.

**Scale/Scope**: MVP audience (few active users). Three tools,
two endpoints (`POST /api/v1/journey/`, `POST
/api/v1/journey/transcribe/`), one frontend panel.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I (MVP validation first)**: PASS — the helper is the interface
  that answers the narrowed validation question (route/stop
  discovery and service availability) for real passengers.
- **II (read-only public product)**: PASS — tools are read-only;
  no new feedback or editing surface is introduced.
- **III (no accounts, minimal data)**: PASS — no login, no
  tracking, no per-user memory; voice audio is transcribed and
  discarded, never stored or logged.
- **IV (monorepo separation)**: PASS — frontend reaches the
  helper only through versioned REST; the model SDK lives in
  `backend/` only.
- **V (app-owned data + provenance)**: PASS — tools query the
  owned PostgreSQL dataset (002/003), never OSM live; provenance
  stays stored and hidden as before.
- **VI (simple stack, deferred complexity)**: PASS with one
  recorded justification — the only external call is the
  constitution- and requester-mandated Meta model API via SDK
  (no new service, queue, cache, router, or planner). See
  Complexity Tracking.
- **VII (Django Admin)**: PASS — no admin changes; no new
  management UI.
- **VIII (schedule gating)**: PASS — the verifier strips or
  refuses any times; no timetable entities are read or exposed.
- **IX (Meta AI)**: PASS — declared models via backend SDK;
  read-only JSON-schema tools, MCP-compatible, no MCP server;
  evidence-only answers, refusal, disambiguation, `/routes/:id`
  evidence links; editable transcripts, no audio retention;
  model/provider/latency in meta and logs; distinct unverified
  rendering; data minimisation throughout.

Post-design re-check: no new principles engaged; all gates still
pass. One justified external dependency — Complexity Tracking
below.

## Project Structure

### Documentation (this feature)

```text
specs/004-journey-agent/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   ├── journey.md       # POST /api/v1/journey/ request/response, meta, tools
│   └── transcribe.md    # POST /api/v1/journey/transcribe/ audio in, transcript out
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── config/
│   ├── settings.py                # EXTEND: MODEL_API_KEY, model names, timeouts (no new auth defaults)
│   └── urls.py                    # EXTEND: mount journey API under api/v1/
└── apps/
    ├── journey/                   # NEW: agentic journey helper
    │   ├── __init__.py
    │   ├── providers/
    │   │   └── meta.py            # OpenAI SDK client (base_url https://api.meta.ai/v1, Bearer MODEL_API_KEY)
    │   ├── tools.py               # search_stops, find_routes, get_route_detail (read-only) + JSON schemas
    │   ├── agent.py               # tool loop (muse-spark-1.3), verifier, refusal/disambiguation, fallback
    │   ├── views.py               # journey + transcribe endpoints (POST only, AllowAny, throttled)
    │   ├── urls.py                # journey routes under api/v1/
    │   └── tests/                 # stubbed-model tests (no network)
    └── transport/api/             # REUSE ONLY: servable/order/pagination helpers (no edits expected)
frontend/
└── src/
    ├── components/
    │   └── JourneyPanel.jsx       # NEW: chat, evidence links, unverified label, voice button
    └── services/
        └── journey.js             # NEW: REST client for journey + transcribe (no model calls)
```

**Structure Decision**: The helper is a new `apps/journey/` app
because it owns new behaviour (agent loop, tools, verification)
that is not a read projection of transport data; it reuses the
003 transport query helpers rather than duplicating them, and the
frontend consumes it only through the versioned REST boundary.
No new app for AI generally — journey and future feedback
intelligence share this seam via separate tools, not separate
services.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| External model API calls at request time (Principle VI: synchronous stack, no new services) | Constitution Principle IX *requires* declared Meta models called via backend SDK, and the requester fixed the model, SDK, and endpoint; evidence-grounded answers cannot be produced without the model call | Pure-DB template answers cannot disambiguate, refuse gracefully, or speak in everyday language — the validation question needs a conversational helper, not canned strings; no new infrastructure (queue/cache/service) is introduced, only HTTPS calls from the existing web process |

