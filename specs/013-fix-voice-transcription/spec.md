# Feature Specification: Fix Voice Search Transcription

**Feature Branch**: `013-fix-voice-transcription`

**Created**: 2026-11-02

**Status**: Draft

**Input**: User description: "Fix voice search transcription: backend POSTs to wrong Meta endpoint and sends incompatible audio shape, so every dictation fails. Keep UX unchanged: press-and-hold Dictate, editable transcript, send edited text to journey, retain no audio. Acceptance: successful dictation returns 200 transcript; missing/empty/oversized audio returns plain 400; upstream outage returns plain cannot-transcribe; no audio, transcript, or key in logs/frontend; WAV requirement satisfied; stop-name bias preserved via keywords; English bias preserved."

## Clarifications

### Session 2026-11-02

- Q: Which audio shape does the transcription endpoint require? → A: WAV (stated in the request; plan confirms the exact endpoint path and payload against the provider docs before implementing).
- Q: Should the Dictate UX change in any way? → A: No — press-and-hold recording, editable transcript field, and sending only the edited text to the journey question stay exactly as they are.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Successful dictation returns an editable transcript (Priority: P1)

A passenger presses and holds Dictate, speaks a journey question, and releases. The backend transcribes the audio through the correct Meta transcription endpoint and returns the text, which lands in the editable question field. The passenger can correct the wording and sends only the edited text to the journey helper.

**Why this priority**: This is the reported defect. Every dictation currently fails, so voice input is entirely unusable.

**Independent Test**: Record a clear spoken question, post it to the transcribe endpoint, and confirm a 200 response carrying a non-empty transcript that the UI places in the editable field.

**Acceptance Scenarios**:

1. **Given** a clear spoken journey question, **When** the passenger dictates it, **Then** the endpoint returns 200 with a non-empty `transcript` plus `meta` (model, provider, latency), and the UI shows the text in the editable field.
2. **Given** a dictated transcript, **When** the passenger edits the wording and asks, **Then** only the edited text is sent to the journey question endpoint.

---

### User Story 2 - Invalid audio is refused plainly, never guessed (Priority: P1)

A dictation arrives with missing, empty, undecodable, or oversized audio. The helper refuses in plain language instead of inventing a transcript, so the passenger knows to try again.

**Why this priority**: A guessed transcript sends the passenger down the wrong journey. Honest refusal is the safe failure mode and is already the contracted behavior that must keep working after the endpoint fix.

**Independent Test**: Post each invalid shape (no audio part, zero-byte file, random non-audio bytes, over-5 MB file) and confirm each returns the plain-language 400 with no transcript.

**Acceptance Scenarios**:

1. **Given** a request with no audio part or an empty file, **When** it reaches the transcribe endpoint, **Then** it returns a plain-language 400 naming the problem and no transcript.
2. **Given** audio larger than 5 MB, **When** it is uploaded, **Then** it is rejected with the plain-language 400 before any model call.
3. **Given** undecodable bytes, **When** transcription is attempted, **Then** the response is the plain-language cannot-transcribe message, never a fabricated transcript.

---

### User Story 3 - Upstream outage and privacy hold under failure (Priority: P2)

The Meta transcription service is unreachable or errors. The passenger still gets a plain-language cannot-transcribe message within the bounded retry budget, and nothing spoken is retained or logged anywhere — on success or failure.

**Why this priority**: Voice input handles personal speech. The no-retention guarantee is a constitution-level constraint that the endpoint fix must not weaken.

**Independent Test**: Point the backend at an unreachable transcription endpoint (or stub an outage), dictate, and confirm the plain-language message; then audit server storage, logs, and the frontend bundle for any audio, transcript, or key material.

**Acceptance Scenarios**:

1. **Given** the transcription upstream is down, **When** the passenger dictates, **Then** the endpoint returns the plain-language cannot-transcribe message after at most one retry, without hanging past the timeout budget.
2. **Given** any dictation (success or failure), **When** the request completes, **Then** no audio bytes, transcript text, or model key exist on disk, in the database, in logs, or in frontend code.

---

### Edge Cases

- Frontend encode failure (captured audio undecodable, WebAudio decode rejects): Dictate MUST show the plain-language cannot-transcribe notice, upload nothing, and leave the editable field focused so the passenger can type the question instead.
- Empty transcript from the model: treated like undecodable audio — plain cannot-transcribe message, never an empty answer presented as success.
- Non-POST verbs on the transcribe path: refused with 405 in the shared plain-language shape (existing contract, unchanged).
- Missing server-side model key: plain cannot-transcribe message; the key name and absence reason never reach the client.
- Throttling (429 with `Retry-After`): unchanged shared behavior.
- Browser without microphone access: existing frontend denial path, unchanged (no backend change).
- Audio exactly at the 5 MB bound: accepted; one byte over is rejected (boundary preserved as-is).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The backend MUST POST transcription requests to `https://api.meta.ai/v1/asr/transcribe` as `multipart/form-data` with a `request` JSON part plus the `audio` part, replacing the current wrong endpoint and incompatible shape.
- **FR-002**: The frontend MUST encode dictated audio as mono 16-bit PCM WAV at 24 kHz (16 kHz accepted) and upload it as `question.wav` (`audio/wav`); the backend MUST validate the WAV header (mono, 16-bit PCM, 16 or 24 kHz), normalize the filename to `*.wav`, enforce the 5 MB bound on the upload, and MUST NOT run a transcode fallback. The MIME change is not a UX change.
- **FR-003**: Missing, empty, oversized, or non-WAV audio MUST be rejected with the plain-language 400 before any model call; no transcript is ever guessed.
- **FR-004**: The success contract MUST stay unchanged: 200 with `{transcript, meta: {model, provider, latency_ms}}`; the transcript lands in the editable field and only edited text is ever sent to the journey endpoint.
- **FR-005**: Upstream timeout/connection errors MUST get at most one bounded retry, then the plain-language cannot-transcribe message (existing retry budget unchanged).
- **FR-006**: Audio bytes, transcript text, and the model key MUST NOT be written to disk, database, or cache, MUST NOT appear in logs, and MUST NOT appear in frontend code — on success and on every failure path.
- **FR-007**: The `request` JSON part MUST carry `languageBias: ["english"]` (lowercase, matching the reference client) and MUST NOT carry `keywords`. Stop-name vocabulary biasing is intentionally omitted: live probing against the endpoint showed it rejects arbitrary stop-name content with a 400 that fails the whole transcription (the stop "Aarow Global Business Solutions" failed alone while every other probed name passed, and the rule is not length, word count, or list size, so no safe subset can be constructed). Transcription relies on the base model with no bias hints.
- **FR-008**: The Dictate UX MUST NOT change: press-and-hold recording, editable transcript field, and sending only the edited text to the journey question.
- **FR-009**: The model key MUST stay server-side only, used exclusively through server-side HTTPS (direct `httpx` call; the SDK is not used for transcription).
- **FR-010**: The request MUST send `Accept: application/json`; the backend MUST parse `TranscribeResponse.transcript`, and an empty transcript MUST return the plain 400, never presented as success.

### Key Entities

- **Audio upload**: Transient spoken question bytes (multipart `audio` part, ≤5 MB); used for one transcription call only and never stored.
- **Transcript**: The returned text plus `meta` (model, provider, latency_ms); placed in the editable field, never logged or retained server-side.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A clear dictated question returns a 200 response with a non-empty transcript placed in the editable field.
- **SC-002**: Missing, empty, undecodable, and oversized audio each return the plain-language refusal with no transcript — zero guessed transcripts in trials.
- **SC-003**: During a simulated upstream outage, every dictation returns the plain-language message within the timeout-plus-one-retry budget (no hangs).
- **SC-004**: An audit after dictated trials finds no audio bytes, transcript text, or model key material on disk, in the database, in logs, or in the frontend bundle.

## Assumptions

- The exact Meta endpoint path and WAV payload shape are confirmed against the provider docs during planning (the request states both are currently wrong).
- The frontend encodes dictated audio as WAV (`question.wav`); there is deliberately no backend transcode fallback.
- The `muse-voice-transcribe-1.0` model name stays; English bias is carried as `languageBias: ["english"]` (lowercase) in the `request` part.
- Model calls in tests stay stubbed at the `httpx` boundary; no live key or network is needed for the suite.
- The 5 MB bound, 405/429 behavior, and throttle classes are reused as-is.
