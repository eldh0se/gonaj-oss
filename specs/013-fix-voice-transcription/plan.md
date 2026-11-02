# Implementation Plan: Fix Voice Search Transcription

**Branch**: `main` (spec `013-fix-voice-transcription`; no feature branch cut) | **Date**: 2026-11-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/013-fix-voice-transcription/spec.md` plus the requester's wire decisions (direct `httpx` POST to the Meta ASR endpoint, `request` JSON + WAV audio parts, frontend WAV encode with backend WAV validation and no transcode fallback).

## Summary

Replace the incompatible OpenAI-SDK transcription call with a direct
`httpx` HTTPS POST to `https://api.meta.ai/v1/asr/transcribe`
carrying a `request` JSON part (`model`, `audioEncoding: WAV`, `mode:
PUSH_TO_TALK`, `languageBias: ["English"]`, stop-name `keywords`) plus
the `audio/wav` part, parsing `TranscribeResponse.transcript`.
Encode dictated audio as WAV in the frontend; validate WAV at the
backend with no transcode fallback. Update filename/MIME validation,
the provider, views, tests, and the transcribe contract. Public
endpoint shape, 5 MB bound, plain-language errors, audit `meta`, and
the no-retention rule stay unchanged. See [research.md](./research.md)
for all planning-time decisions, [data-model.md](./data-model.md) for
transient shapes, [contracts/](./contracts/) for the wire contract,
[quickstart.md](./quickstart.md) for validation.

## Technical Context

**Language/Version**: Python 3.13, Django + Django REST Framework (per `backend/requirements.txt`)

**Primary Dependencies**: `httpx` (new, direct HTTPS client for the ASR endpoint); existing OpenAI SDK stays for chat completions; no transcode binary — WAV validation only

**Storage**: No schema change; audio and transcripts remain transient (never disk/DB/cache/logs)

**Testing**: Django test runner — stub at the `httpx` boundary in `test_meta.py`; endpoint behavior in `test_transcribe.py`; privacy pinned by the root `test_logging.py` sweep (must stay green)

**Target Platform**: Linux server; single deployable app (web + PostgreSQL)

**Project Type**: web-service (monorepo; backend provider fix plus additive frontend WAV encode in the existing dictate component)

**Performance Goals**: Single-shot dictation within the 20 s timeout plus at most one transient retry; no separate latency target — bounded work instead

**Constraints**: Read-only product (no dataset writes); plain-language errors only (never leak key, upstream detail, audio, or transcripts); 5 MB bound enforced on the upload before any model call; filename normalized to `*.wav` with `audio/wav` validation of mono 16-bit PCM at 16 or 24 kHz (24 kHz preferred; non-WAV rejected plainly, no transcode path); client-side encode failure shows the plain cannot-transcribe notice with typed-input fallback and no upload; `sessionId` omitted from the wire call; response `meta` (model, provider, latency) audit preserved (transcribe has no `tools_used`); tests stub at the `httpx` boundary with no live network

**Scale/Scope**: One endpoint's wire call plus an additive frontend encoder; ≤100 stop-name keywords reused from `_stop_vocabulary`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. MVP validation first** — PASS: restores the core voice-input path ("How do I get from A to B?").
- **II. Read-only product** — PASS: transcription reads audio transiently; no dataset mutation, no admin changes, no crowdsourcing mechanics; audio discarded same-request.
- **III. No accounts / minimal data** — PASS: no identity or tracking; audio never stored; logs carry no audio, transcript, or key (sweep-tested).
- **IV. Monorepo separation** — PASS: `backend/` provider fix plus additive WAV encode in the existing dictate component; public API shape unchanged; no cross-boundary internals.
- **V. App-owned GTFS-inspired data + provenance** — PASS: reads existing stop names for keyword bias only; no OSM-live queries; provenance untouched.
- **VI. Simple synchronous stack** — PASS: plain Python + Django; `httpx` is a synchronous HTTP client, not a new service, queue, or routing engine; no transcode binary — WAV validation only.
- **VII. Admin as data interface** — N/A: no data-management change.
- **VIII. Schedule gating** — PASS: no times, durations, or frequencies involved.
- **IX. Meta AI integration** — PASS with recorded justification: the call stays a direct backend integration against the declared Meta endpoint and model, key server-side only, tools read-only with JSON-compatible shapes, answers evidence-grounded with refuse-on-unknown, and model/provider/latency meta exposed. The OpenAI SDK remains for chat; only the transcription leg moves to `httpx` because the SDK's fixed `/audio/transcriptions` shape is the reported defect. No MCP server is stood up.

*Re-check after Phase 1 design (2026-11-02): still PASS on all gates. Design adds one HTTP client dependency; no service, migration, endpoint, tracking, or privacy change; the wire contract is documented, not widened.*

## Project Structure

### Documentation (this feature)

```text
specs/013-fix-voice-transcription/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── asr-wire.md      # corrected backend→Meta wire call (public contract unchanged, see 004)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── apps/
│   └── journey/
│       ├── providers/
│       │   └── meta.py    # transcribe_audio via httpx + _with_one_retry; chat path untouched
│       ├── views.py       # transcribe: WAV filename/MIME validation, unchanged shapes/bounds/errors
│       └── tests/         # test_transcribe.py (endpoint), test_meta.py (httpx boundary stubs)
└── requirements.txt       # add httpx
frontend/
└── src/components/
    └── JourneyPanel.jsx   # WAV-encode dictated audio client-side (no new dependency)
```

**Structure Decision**: Backend provider fix plus a small additive frontend encoder in the existing dictate component. The public transcribe contract is unchanged (see 004); only the backend→Meta wire shape and upload validation change. No migration: zero schema change.

## Complexity Tracking

> No constitution violations — table intentionally empty (IX justified above, not violated).
