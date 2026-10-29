# Quickstart: Journey Agent

**Feature**: [spec.md](spec.md) | **Date**: 2026-10-29

Validates the feature end to end against
[contracts/journey.md](contracts/journey.md) and
[contracts/transcribe.md](contracts/transcribe.md). Backend
checks run against stubbed model clients (no network, no key);
the live-model path is a manual reviewer step. Examples assume
the server from `docs/setup-backend.md` with the imported
dataset loaded; substitute real `id` values from the list
responses.

## Prerequisites

- Backend scaffold working per `docs/setup-backend.md`
  (database up, migrations applied, `createcachetable` done).
- Dataset imported per `specs/002-osm-snapshot-import` and the
  read API serving per `specs/003-read-map-api`.
- Automated path needs no model key (stubs). Manual live-model
  checks need `MODEL_API_KEY` exported server-side only.

## 1. Ask and receive an evidence-grounded answer (Story 1)

1. `POST /api/v1/journey/` with
   `{"question": "How do I get from <known origin> to <known destination>?"}` —
   expect `200`, `status: "ok"`, named boarding/alighting
   stops, at least one route with an `evidence` link, and
   `meta` carrying model, provider, and `latency_ms`.
2. Follow one `evidence` link — expect the `200` route detail
   from the read API showing both stops in order.
3. Inspect the answer text — expect no times, durations, or
   transfer instructions of any kind.
4. Ask about two stops with no direct service — expect `200`,
   `status: "refuse"`, a plain-language message, and nothing
   invented.

## 2. Disambiguation (Story 2)

1. Ask with an ambiguous stop name — expect `200`,
   `status: "disambiguate"`, all candidates named, and no
   journey answer yet.
2. Reply choosing one candidate (name it, or send its id in
   `context.candidate_stop_ids`) — expect the follow-up to
   meet Step 1's answer rules for the chosen stop.
3. Ask with a stop name matching nothing — expect a
   plain-language not-found message with spelling/map
   guidance, and no invented stop.

## 3. Voice input (Story 3)

1. Record a journey question and `POST
   /api/v1/journey/transcribe/` with the audio part — expect
   `200` with `transcript` and transcribe-model meta.
2. Edit a word in the transcript in the UI and send — expect
   the answer to reflect the edited text.
3. Review server, database, cache, and logs — expect zero
   bytes of audio retained anywhere.

## 4. Transparency (Story 4)

1. For any journey answer, confirm `meta` carries model ID,
   provider, and `latency_ms`.
2. Find the request's server log line — expect the same model,
   provider, latency, plus the ordered `tools_used` list.
3. In the UI, confirm the answer renders distinctly as AI
   output labelled unverified, with clickable evidence links.

## 5. Read-only and open-access proof (FR-003, FR-017)

1. Run the agent test suite with the model stubbed to attempt
   a write (mutating tool call, feedback rejection, record
   creation) — expect the attempt blocked and logged, with 0
   writes performed.
2. Repeat Steps 1–4 with no credentials or cookies — expect
   identical results and no tracking headers.
3. Confirm the frontend bundle contains no model key and makes
   no model calls directly (the only AI traffic is to the two
   REST endpoints).

## 6. Failure behaviour (FR-018, fallback)

1. With the model client stubbed unreachable (or the key
   removed), ask any journey question — expect the
   plain-language cannot-answer message (after one retry),
   never an ungrounded answer or a technical dump.
2. Stub the model to return a hallucinated route and a time —
   expect the verifier to refuse (no repair possible) with
   nothing unverifiable delivered.

## Automated suite

Run the journey tests (`apps/journey/tests/`): stubbed-model
tests for answer, disambiguation, refusal, evidence
verification, time/transfer stripping, meta/logs, tool
read-only enforcement, transcript editing, and the no-retention
invariant (spec SC-001–SC-008).

## Done when

All six steps succeed, the automated suite is green, and review
confirms no schedule content, no provenance, and no masters in
any AI-facing surface, with no audio, accounts, tracking, or
per-user memory introduced (Principles III, V, VIII, IX).

