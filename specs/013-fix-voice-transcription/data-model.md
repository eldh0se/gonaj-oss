# Data Model: Fix Voice Search Transcription

**Feature**: `013-fix-voice-transcription` | **Date**: 2026-11-02

No migrations: no schema change. All entities below are transient
(in-request only) or wire shapes.

## AudioUpload (transient)

Spoken question bytes from the existing multipart `audio` part.

- `bytes`: raw upload, at most 5 MB (enforced before any model call); mono 16-bit PCM at 16 or 24 kHz (24 kHz preferred — the endpoint's native rate; other rates get HTTP 503).
- `mime`: `audio/wav` only; anything else gets the plain 400.
- `filename`: normalized to `*.wav` (`question.wav`, replacing `question.webm`).
- Lifecycle: used for one transcription call, then discarded in the
  same request. Never written to disk, database, or cache; never logged.

## Transcript (transient result)

- `transcript`: non-empty text from `TranscribeResponse.transcript`;
  empty text is treated as failure (plain cannot-transcribe message).
- `meta`: `{model: "muse-voice-transcribe-1.0", provider: "meta",
  latency_ms}` — audited in logs and response, unchanged shape.
- Lifecycle: returned to the UI for the editable field; never logged
  or retained server-side (log sweep test pins this).

## MetaASRRequest (wire shape, backend → Meta)

`POST https://api.meta.ai/v1/asr/transcribe`, 20 s timeout, at most
one retry on timeout/connection errors:

- `request` JSON part: `{model: "muse-voice-transcribe-1.0",
  audioEncoding: "WAV", mode: "PUSH_TO_TALK",
  languageBias: ["english"], keywords: [<stop names>]}`.
- Audio part: WAV bytes as `audio/wav`.
- Headers: `Accept: application/json`, `Authorization: Bearer <key>`
  (server-side key, unchanged handling).

## Validation rules (unchanged unless noted)

- Missing/empty/undecodable/non-WAV audio → plain-language 400, no transcript.
- Oversized audio (> 5 MB) → plain-language 400 before any model call.
- Upstream timeout/connection error → one retry, then plain-language
  cannot-transcribe message.
