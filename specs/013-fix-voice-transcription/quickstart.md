# Quickstart: Fix Voice Search Transcription

**Feature**: `013-fix-voice-transcription` | **Date**: 2026-11-02

Validates the corrected transcription wire end to end. All backend
checks run without a live key or network (stubbed at the `httpx`
boundary); one optional manual pass exercises real dictation.

## Prerequisites

- Backend deps installed; Postgres running (`docs/setup-backend.md`).
- `DJANGO_SECRET_KEY` set (any dev value); no model key needed for
  the stubbed suite.

## 1. Unit + contract suite (stubbed)

```sh
cd backend
../.venv/bin/python manage.py test apps.journey.tests.test_transcribe apps.journey.tests.test_meta tests.test_logging -v 1
```

Expected: green. Covers the 200 transcript shape, missing/empty/
oversized/decodable-audio 400s, outage-after-retry message, WAV
MIME/filename validation, and the no-private-content log sweep.

## 2. WAV contract probe (no network)

Post a 24 kHz mono 16-bit PCM WAV fixture and a webm fixture to the
local endpoint; confirm the WAV is accepted for transcription and
non-WAV gets the plain 400 before any model call (no transcode path):

```sh
curl -s -o /dev/null -w "%{http_code}\n" -F "audio=@q.wav" \
  http://localhost:8000/api/v1/journey/transcribe/
```

## 3. Manual dictation (optional, needs key + mic)

Set `MODEL_API_KEY`, run the dev server and frontend, press-and-hold
Dictate and speak. Expected: editable transcript appears; edited
text answers via the journey endpoint; server logs and responses
contain no audio, transcript, or key material.

## 4. Scenario map

- Quickstart 1–2 pin User Story 1 (200 + editable field).
- Quickstart 1 pins User Story 2 (400s, never guessed).
- Outage stub + log audit pin User Story 3.
- Details: [data-model.md](./data-model.md), [contracts/asr-wire.md](./contracts/asr-wire.md), public contract in [004](../../004-journey-agent/contracts/transcribe.md).
