# Contract: Transcribe Endpoint

**Feature**: [spec.md](../spec.md) | **Date**: 2026-10-29

`POST /api/v1/journey/transcribe/` — voice input mode only.
Accepts audio, returns an editable transcript, and retains
nothing. Unauthenticated and untracked; throttled with the other
reads. GET and other non-POST verbs are refused (`405`, shared
plain-language shape).

## Request

`multipart/form-data` with a single audio part:

| Part | Required | Meaning |
|------|----------|---------|
| `audio` | yes | Spoken journey question (device microphone, PUSH_TO_TALK UX). Bounded size (plan: 5 MB); larger uploads are rejected with the plain-language 400. |

Missing or undecodable audio returns the plain-language
cannot-transcribe message (never a guessed transcript).

## Success response — `200`

```json
{
  "transcript": "How do I get from Ernakulam South to Fort Kochi?",
  "meta": { "model": "muse-voice-transcribe-1.0", "provider": "meta", "latency_ms": 900 }
}
```

- `transcript` is placed by the UI into an editable field; only
  the edited text is ever sent to `POST /api/v1/journey/`
  (see [journey.md](journey.md)).
- Transcription uses English language bias plus stop-name
  vocabulary biasing so stop names survive dictation.
- The audio bytes are discarded in the same request: never
  written to disk, database, or cache, and never logged.

## Errors

All errors use the shared plain-language `{"detail"}`
shape: missing/undecodable/oversized audio, model
unavailable (after one bounded retry), and throttling
(`429` with `Retry-After`).

## Non-goals (explicitly out of contract)

- Audio storage, playback, or quality review of any kind.
- Speaker identification or voice profiles.
- Client-side transcription (the model key must never reach
  the device).

