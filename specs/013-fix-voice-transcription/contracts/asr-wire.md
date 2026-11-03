# Contract: Meta ASR Wire Call (backend → Meta)

**Feature**: [spec.md](../spec.md) | **Date**: 2026-11-02

The public `POST /api/v1/journey/transcribe/` contract is unchanged —
see [004's transcribe contract](../../004-journey-agent/contracts/transcribe.md)
(request shape, 200 shape, plain-language errors, no-retention rule).
This file pins the corrected server-to-Meta wire call that replaces the
incompatible OpenAI-SDK `audio.transcriptions` shape.

## Request

`POST https://api.meta.ai/v1/asr/transcribe` via `httpx`
(timeout 20 s, at most one retry on timeout/connection errors).

`multipart/form-data` with two parts:

| Part | Content-Type | Meaning |
|------|--------------|---------|
| `request` | `application/json` | `{model: "muse-voice-transcribe-1.0", audioEncoding: "WAV", mode: "PUSH_TO_TALK", languageBias: ["english"]}` — no `keywords` key (biasing removed, see Errors) |
| `audio` | `audio/wav` | Spoken question bytes: mono 16-bit PCM WAV at 16 or 24 kHz (24 kHz preferred), filename normalized to `*.wav` (WAV requirement; other rates get HTTP 503) |

Headers: `Accept: application/json`, `Authorization: Bearer <server-side key>`. No `sessionId` is sent.

## Success response

HTTP 200, JSON body parsed as `TranscribeResponse`; the backend uses
`.transcript`. An empty transcript is treated as failure (plain
cannot-transcribe message), same as undecodable audio today.

## Errors

- Timeout/connection error → one retry, then the plain-language
  cannot-transcribe message (existing 400 shape, no key or upstream
  detail leaked).
- Upstream non-200 / malformed body → same plain-language message.
- No `keywords` are sent: live probing showed the endpoint rejects
  arbitrary vocabulary content (e.g. one stop name fails while every
  other probed name passes, independent of length, word count, and
  list size), and a single rejected keyword 400s the whole
  transcription — so vocabulary biasing is omitted by design.

## Non-goals

- Changing the public endpoint shape, throttle, 5 MB bound, or audit
  `meta` fields.
- Logging or retaining audio, transcripts, or the key (sweep-tested).
