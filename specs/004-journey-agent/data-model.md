# Data Model: Journey Agent

**Feature**: [spec.md](spec.md) | **Date**: 2026-10-29

No new tables. The agent is stateless per request: everything
below is transient in-request state except the server log line.
Canonical transit data is read through the existing `Stop`,
`Route`, `RouteStopMembership`, `RouteMaster`, and
`RouteMasterMembership` tables via the shared 003 query helpers
(`servable_routes`, `order_routes`). Field shapes are normative
in [contracts/journey.md](contracts/journey.md) and
[contracts/transcribe.md](contracts/transcribe.md).

## Journey Request (transient, never stored)

One passenger question as received by `POST /api/v1/journey/`.

- Carries: `question` (typed text or edited transcript,
  required, non-blank), optional `history` (prior turns, bounded
  to the last 6, used only for this request's disambiguation
  follow-ups), optional `context` (candidate stop ids from a
  previous disambiguation prompt).
- Validation: blank question → ask-again prompt, never a model
  call; history beyond 6 turns is ignored; candidate ids that
  no longer resolve are treated as unknown stops.
- Relationships: resolves (via tools) to zero or more Stops;
  produces one Answer, Refusal, or Disambiguation prompt.

## Tool Call (transient, logged by name)

One model-invoked `search_stops`, `find_routes`, or
`get_route_detail` execution within a request.

- Carries: tool name, JSON arguments (per the contract
  schemas), the read-only ORM result, and the fact that
  nothing was written.
- Validation: arguments outside the schema are rejected before
  execution; any tool raising (bad id, no match) returns an
  empty/error result to the loop, never an exception to the
  passenger.
- Relationships: reads canonical tables only; the ordered tool
  names are recorded in the server log (`tools_used`).

## Evidence-Grounded Answer (transient response)

One delivered journey answer.

- Carries: the answer text (everyday language, no times, no
  transfers), the resolved boarding/alighting stop names
  (FR-021), cited routes each with `/routes/:id` evidence, and
  `meta: {model, provider, latency_ms}`.
- Validation (server-side verifier, before delivery): every
  cited route must contain both resolved stops in travelling
  order on a servable route; any time/transfer-shaped content
  fails verification; one repair attempt, then refusal.
- Relationships: evidence links resolve to existing route
  detail; meta values match the server log line.

## Refusal / Disambiguation Prompt (transient response)

One honest non-answer.

- Carries: the plain-language reason (unknown connection,
  unknown stop, model unavailable) or the candidate stop list
  with their ids for the follow-up request's `context`.
- Validation: carries no route claims, no times, no links to
  nonexistent routes; disambiguation names all candidates.
- State transitions: disambiguation → (passenger picks) →
  Answer or Refusal for the chosen stop. No server-side state
  is kept between the two requests.

## Transcript (transient response)

The text returned by `POST /api/v1/journey/transcribe/`.

- Carries: `transcript` text plus the transcribe model ID.
  The source audio bytes are discarded in the same request;
  nothing audio-shaped is written to disk, database, cache,
  or logs.
- Validation: empty or unintelligible audio → a plain
  cannot-transcribe message, never a guessed transcript.

## Response Meta (transient, mirrored in logs)

`{model, provider, latency_ms}` on every journey and transcribe
response; the server log line for the request records model,
provider, latency, and ordered `tools_used`. The fallback uses
model `none`, provider `local-fallback`, and measured latency.

## Deliberately absent

No `Conversation`, `Session`, `Transcript`, or `AudioClip`
tables; no per-user memory of any kind (FR-017). No `Trip`,
`StopTime`, or schedule reads (Principle VIII). No feedback
records from this feature (feedback intelligence is separate).
No API keys, user profiles, or tracking identifiers anywhere.

