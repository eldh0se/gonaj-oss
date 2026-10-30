# Research: Journey Agent

**Feature**: [spec.md](spec.md) | **Date**: 2026-10-29

The requester fixed the stack at plan time (models, SDK, auth,
tools, session, verifiability) with reference docs
(`https://dev.meta.ai/docs/authentication`,
`/docs/models`, `/docs/speech-to-text`,
`/docs/cookbook` tool-function-calling, structured-output,
error-handling-retry, voice-api-fundamentals). No NEEDS
CLARIFICATION remained. Each decision below records what was
chosen, why, and what was set aside. Endpoint shapes are
normative in [contracts/](contracts/).

## Decision: Declared models are muse-spark-1.3 (tool loop) and muse-voice-transcribe-1.0 (voice)

- **Decision**: The tool loop runs on `muse-spark-1.3`; voice
  transcription uses `muse-voice-transcribe-1.0` PUSH_TO_TALK
  with languageBias English and stop-name vocabulary biasing
  (bias list built from the stop table at request time, capped
  to the highest-frequency names). Model IDs are settings,
  declared per FR-019 and echoed in every response meta.
- **Rationale**: Requester-mandated and constitution-compatible;
  settings-level declaration keeps the choice reviewable and
  swappable without code changes, and vocabulary biasing
  directly serves disambiguation (Story 2).
- **Alternatives considered**: Any other model (rejected — the
  requester declared these two); hardcoding IDs in code
  (rejected — FR-019 requires a named, reviewable declaration).

## Decision: OpenAI SDK against https://api.meta.ai/v1, Bearer MODEL_API_KEY server-side only

- **Decision**: A single backend provider module wraps the OpenAI
  SDK configured with `base_url="https://api.meta.ai/v1"` and
  `Authorization: Bearer MODEL_API_KEY` read from the server
  environment (`MODEL_API_KEY`, fail-fast when absent). The key
  never leaves the server: it appears in no response, log, or
  frontend bundle. Per the authentication reference, only
  server-side issuance/storage is used.
- **Rationale**: Matches the requester directive and the
  reference auth pattern exactly, while satisfying FR-001 and
  Principle IX (frontend never calls models).
- **Alternatives considered**: Frontend-held key or proxied
  per-user keys (rejected — leaks credentials and implies user
  identity); a second SDK (rejected — one client, one seam).

## Decision: Three read-only JSON-schema tools over canonical tables, no MCP server

- **Decision**: `search_stops` (text/bbox over `Stop`, same
  semantics as the 003 stops list), `find_routes`
  (`from_stop_id`/`to_stop_id`, same-servable-route
  order-aware containment as 003 connectivity), and
  `get_route_detail` (one route: fields plus ordered stops).
  Each is a plain Python function over the Django ORM reusing
  the 003 `transport.api` queryset helpers
  (`servable_routes`, `order_routes`, envelope-free full
  results), each carries an explicit JSON schema, and the
  schemas are kept MCP-compatible. No MCP server is stood up;
  the model calls the functions through the SDK's function-calling
  shape only.
- **Rationale**: Reuse keeps one definition of "servable" and
  "in order" instead of two; explicit schemas make the tool
  surface testable without the model; MCP-compatibility without
  a server is exactly what Principle IX prescribes.
- **Alternatives considered**: HTTP self-calls to `/api/v1/`
  from tools (rejected — adds auth/throttle/serialisation
  round-trips inside the request and couples tools to URL
  wiring); duplicated query logic (rejected — two definitions
  of servable would drift); a fourth schedule tool (rejected —
  Principle VIII, no schedule data exists).

## Decision: Server-side verifier admits only evidence-verified direct connections

- **Decision**: Before any model draft reaches the passenger, the
  verifier requires, for every cited route, that both resolved
  stops occur on that servable route in travelling order
  (`from_position < to_position`, same check as
  `find_routes`). Any cited route failing verification, and any
  draft containing time-, duration-, frequency-, or
  transfer-shaped content, is refused or stripped; after one
  repair attempt the helper refuses plainly. Disambiguation
  (multiple stop matches) and unknown-stop/unknown-connection
  cases never reach the model as answerable — they return the
  Story 2/Story 1 refusal or candidate prompt directly.
- **Rationale**: The model is the eloquence layer, never the
  source of truth; verification is what makes SC-001/SC-002
  testable without trusting model output.
- **Alternatives considered**: Trusting the model's citations
  (rejected — hallucinates routes/times, the exact failure
  Principle IX forbids); client-side verification (rejected —
  evidence checks need canonical data the frontend must not
  touch directly).

## Decision: Stateless per request; client may send bounded history; server retains nothing

- **Decision**: The server holds no session store. The journey
  request body may include prior turns (bounded: last 6), which
  are used only for that request's disambiguation follow-ups
  and then dropped. Disambiguation state (candidate stop ids)
  travels in the request/response payload, never in server
  memory, cache, or database.
- **Rationale**: Satisfies FR-017 (no per-user memory) with the
  least machinery: follow-up questions work, but there is
  literally nowhere for tracking state to accumulate.
- **Alternatives considered**: Server-side sessions or cache
  (rejected — retention surface for zero product gain);
  no-history single-shot only (rejected — disambiguation
  follow-ups need the candidate context, which the stateless
  payload already carries).

## Decision: 20 s timeout, one retry, then the non-AI fallback

- **Decision**: Each model call has a 20-second timeout; one
  retry on timeout/transient error, then the non-AI fallback:
  a plain-language message plus deterministic results computed
  without the model (the direct `find_routes` outcome for
  resolved stops, or the browse guidance for unresolved ones),
  labelled as non-AI (provider `local-fallback`, model `none`)
  with latency measured the same way. Per the error-handling
  reference, retries are bounded and idempotent-safe (reads
  only).
- **Rationale**: Bounded waiting keeps the chat responsive for
  an MVP audience; the fallback preserves usefulness during
  model outages without ever inventing content.
- **Alternatives considered**: Longer timeouts or unbounded
  retries (rejected — a hung chat is worse than an honest
  fallback); silent failure (rejected — FR-018 requires the
  plain-language cannot-answer message).

## Decision: Voice is transcribe-then-discard with editable transcript

- **Decision**: The frontend records with the device microphone
  (PUSH_TO_TALK UX: press-and-hold button) and POSTs the audio
  to `/api/v1/journey/transcribe/`; the backend transcribes via
  `muse-voice-transcribe-1.0` with English bias plus stop-name
  vocabulary biasing, returns `{transcript}`, and discards the
  audio bytes without writing them anywhere. The UI places the
  transcript in an editable field; only the edited text is ever
  sent to `/api/v1/journey/`. Audio never reaches logs, the
  database, or the cache.
- **Rationale**: Satisfies Story 3 exactly — input mode with
  human correction and zero retention — following the
  voice-api-fundamentals reference.
- **Alternatives considered**: Client-side transcription
  (rejected — would need the model key or a second speech
  dependency on the device); storing audio for "quality"
  (rejected — direct Principles III/IX violation).

## Decision: Meta (model, provider, latency_ms) plus server logs (model, tools_used)

- **Decision**: Every journey response embeds
  `meta: {model, provider, latency_ms}` measured around the
  producing call (fallback: `none`/`local-fallback`/measured
  ms); the server log line for the request records model,
  provider, latency, and the ordered `tools_used` list.
  Transcribe responses carry the voice model ID likewise.
- **Rationale**: FR-013/FR-014 and SC-005 verbatim; logs give
  reviewers the audit trail (which tools ran for which claim)
  without storing user content beyond ordinary server logs.
- **Alternatives considered**: Meta without logs (rejected —
  unauditable); logging full prompts/answers (rejected —
  retains dictated PII against FR-017).

## Decision: Frontend renders AI distinctly, links evidence, labels unverified

- **Decision**: A `JourneyPanel` chat component renders model
  text in a visually distinct AI style with inline `/routes/:id`
  evidence links and a persistent "Unverified AI answer" label;
  deterministic fallback and refusal states use the same label
  family. The panel talks only to the two REST endpoints via a
  thin `journey.js` client — no model SDK in the bundle.
- **Rationale**: FR-015 and SC-005 verbatim; evidence links
  reuse the public route pages the map already serves.
- **Alternatives considered**: Plain unstyled chat (rejected —
  indistinguishable AI output violates Principle IX); linking
  evidence to modal previews (rejected — deferred polish, links
  suffice for MVP).

