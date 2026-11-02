# Research: Fix Voice Search Transcription

**Feature**: `013-fix-voice-transcription` | **Date**: 2026-11-02

All unknowns below were decided by the requester in the plan input;
research records the decisions with rationale and alternatives so
implementation has no open choices.

## Decision 1: Transport — direct httpx POST, not the OpenAI SDK

- **Decision**: Replace `client.audio.transcriptions.create(...)` with a
  direct HTTPS `POST https://api.meta.ai/v1/asr/transcribe` via `httpx`
  (new runtime dependency), 20 s timeout, one retry on transient
  timeout/connection errors by reusing the `_with_one_retry` pattern.
- **Rationale**: The SDK's `audio.transcriptions` request shape is built
  for OpenAI-compatible endpoints and is incompatible with the Meta ASR
  endpoint, so every dictation fails at the wire level. `httpx` is a plain
  synchronous HTTP client: no new service, queue, or routing engine, and
  the call stays server-side through the existing provider module.
- **Alternatives considered**:
  - Keep the SDK and reshape arguments: rejected — the SDK fixes the
    path to `/audio/transcriptions` and the wrong endpoint is the
    reported defect.
  - `requests` instead of `httpx`: rejected — `httpx` timeout/response
    API matches the existing retry helper with less adaptation.

## Decision 2: Wire shape — `request` JSON part plus WAV audio part

- **Decision**: `multipart/form-data` with a `request` JSON part
  `{model: "muse-voice-transcribe-1.0", audioEncoding: "WAV",
  mode: "PUSH_TO_TALK", languageBias: ["English"], keywords: <stop list>}`
  plus the `audio` part (`audio/wav`), `Accept: application/json`,
  no `sessionId`; parse `TranscribeResponse.transcript` (empty
  transcript = failure, same as today).
- **Rationale**: Matches the endpoint's contract exactly: model pin,
  WAV encoding declaration, push-to-talk mode, English bias, and the
  existing stop-name keyword biasing carried over as `keywords`.
- **Alternatives considered**:
  - Single JSON body with base64 audio: rejected — doubles payload size
    and contradicts the endpoint's multipart contract.

## Decision 3: WAV source — frontend encodes, backend validates, no fallback

- **Decision**: The frontend encodes dictated audio as mono 16-bit
  PCM WAV at 24 kHz (16 kHz accepted; captured audio re-encoded
  client-side via WebAudio decode-to-PCM with resampling, no new
  dependency) and uploads it as `question.wav` (`audio/wav`). The
  backend validates WAV only (mono, 16-bit PCM, 16 or 24 kHz header;
  filename normalized to `*.wav`; `audio/wav` MIME; 5 MB bound on the
  upload) and rejects anything else with the plain 400 — a MIME
  change, not a UX change, and no transcode path by design. If
  client-side decode/encode fails, Dictate shows the plain-language
  cannot-transcribe notice, uploads nothing, and leaves the editable
  field focused for typed input.
- **Rationale**: One path instead of two: WAV at the source removes
  any server-side transcode dependency, and the plain 400 keeps the
  no-guess contract for anything that is not WAV. 24 kHz is the
  endpoint's native rate (16 kHz accepted; anything else gets
  HTTP 503), corroborated by independent integrations and endpoint
  write-ups.
- **Alternatives considered**:
  - Backend transcode fallback via `ffmpeg`: rejected — dual paths
    are over-scope; the MIME change does not alter the press-and-hold
    UX.

## Decision 4: Reuse over new code

- **Decision**: Reuse, in this order:
  - View shape, throttle classes, 5 MB bound, and plain-language error
    responses in `backend/apps/journey/views.py` (`transcribe`).
  - `_with_one_retry` bounded-retry helper and `_stop_vocabulary`
    keyword biasing in the provider module.
  - Existing tests as the update base: `test_transcribe.py`
    (endpoint behavior), `test_meta.py` (provider, stubbed at the
    `httpx` boundary instead of the SDK), and the root
    `test_logging.py` sweep (must stay green: no audio, transcript,
    or key in logs).
- **Rationale**: The defect is the wire call, not the endpoint
  contract; smallest diff on the read-only path with the existing
  suite pinning behavior.
- **Alternatives considered**:
  - New transcription service module: rejected — the provider module
    already owns model access, key handling, and retry policy.

## Deferred (out of scope, noted for the next feature)

- Live language detection (non-English dictation): English bias stays.
- Streaming/partial transcripts: single-shot request/response only.
