# Feature Specification: Journey Agent

**Feature Branch**: `004-journey-agent`

**Created**: 2026-10-29

**Status**: Draft

**Input**: User description: "04 journey-agent: Agentic journey helper using declared Meta model via backend SDK. Tools search_stops and find_routes are read-only. Evidence-verified direct connectivity only, no times or transfers, disambiguation, refusal on unknown. Voice via Muse Voice Transcribe with editable transcript, no retention. Expose model, provider, latency in meta and logs. If required I can provide reference documentation."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ask for a direct journey and get an evidence-grounded answer (Priority: P1)

A passenger asks in plain language how to get from one place to
another (for example, "How do I get from Ernakulam South to Fort
Kochi?"). The journey helper answers only when a direct service
exists in the application's own dataset, and every route it cites
links to that route's evidence. When no direct service is known,
it says so plainly instead of guessing.

**Why this priority**: This is the narrowed MVP validation question
itself ("How do I get from A to B?", Principle I as narrowed by
Principle VIII). An evidence-grounded helper that refuses rather
than invents is what makes AI assistance trustworthy.

**Independent Test**: Ask about two stops known to share a direct
route and confirm the answer cites that route with a working
evidence link and contains no times; ask about an unconnected pair
and confirm an honest refusal with no invented service.

**Acceptance Scenarios**:

1. **Given** two stops connected by a direct route in the
   dataset, **When** the passenger asks how to travel between
   them, **Then** the helper names the direct route and links
   every cited route to its evidence at `/routes/:id`.
2. **Given** the same question, **When** the passenger or reviewer
   inspects the answer, **Then** it contains no schedules, no
   departure or arrival times, no durations, and no transfer
   instructions of any kind.
3. **Given** two stops with no direct service between them,
   **When** the passenger asks, **Then** the helper refuses
   plainly, states that no direct service is known, and invents
   no route, time, or transfer.
4. **Given** any journey answer, **When** it is delivered,
   **Then** it is rendered distinctly as AI-generated and labelled
   unverified, and its response meta exposes the model ID,
   provider, and latency.
5. **Given** a journey answer for resolved stops, **When** the
   passenger reads it, **Then** it names the resolved boarding
   and alighting stops in plain words alongside the route
   evidence, so the passenger can see what the helper understood.
6. **Given** the Journey tab, **When** the passenger picks From
   and To stops and searches, **Then** matching direct services
   list with `/routes/:id` evidence links (or a plain
   no-service message), and starting one search clears the
   other search's results so only one answer is ever visible.

---

### User Story 2 - Disambiguate when the request is unclear (Priority: P1)

A passenger asks using a vague or ambiguous place name (for
example, two stops share a similar name). The helper does not
guess which stop is meant; it asks the passenger to choose between
the candidate stops before answering.

**Why this priority**: Guessing a stop is how an invented journey
starts. Disambiguation is the refusal-before-invention rule applied
to ambiguous input (Principle IX), and without it the evidence
guarantee in Story 1 is hollow.

**Independent Test**: Ask with an ambiguous stop name and confirm
the helper returns candidate stops to choose from rather than a
journey answer; then pick one candidate and confirm the follow-up
answer is evidence-grounded for the chosen stop.

**Acceptance Scenarios**:

1. **Given** a journey request naming a stop that matches more
   than one stop in the dataset, **When** the passenger asks,
   **Then** the helper returns the candidate stops and asks the
   passenger to choose, without giving a journey answer yet.
2. **Given** the disambiguation prompt, **When** the passenger
   picks one candidate, **Then** the helper answers for the chosen
   stop following Story 1 (evidence links, no times) or refuses
   following Story 1 if no direct service exists.
3. **Given** a request naming a stop that matches nothing,
   **When** the passenger asks, **Then** the helper says plainly
   that it cannot find that place and suggests checking the
   spelling or picking from the map, without inventing a stop.

---

### User Story 3 - Speak the request instead of typing it (Priority: P2)

A passenger who prefers speaking (or cannot easily type) dictates
the journey question by voice. The dictated words appear as an
editable transcript the passenger can correct before sending, and
no audio is kept afterwards.

**Why this priority**: Voice is an input mode that widens who can
use the helper, but audio retention would violate data
minimisation (Principles III and IX). Editable-transcript plus
no-retention keeps the mode without the tracking.

**Independent Test**: Dictate a journey question, edit a word in
the transcript, and send; confirm the helper answers the edited
text and that no audio is retained.

**Acceptance Scenarios**:

1. **Given** the journey helper, **When** the passenger dictates
   a question via Muse Voice Transcribe, **Then** the transcript
   appears for review and is editable before anything is sent.
2. **Given** an edited transcript, **When** the passenger sends
   it, **Then** the helper answers the edited text, not the
   original dictation.
3. **Given** any voice interaction, **When** it completes,
   **Then** no audio is retained anywhere: not on the device
   beyond the session's needs, not on the server, and not in any
   log.

---

### User Story 4 - See what the AI is and how it answered (Priority: P2)

A passenger (or reviewer) who receives an AI answer can see which
model gave it, who provides it, and how long it took — in the
response itself and in the logs — so AI behaviour stays auditable
and distinct from authoritative data.

**Why this priority**: Transparency is the accountability half of
Principle IX. Evidence links (Story 1) let a passenger verify the
claim; model, provider, and latency let anyone audit the machine
that made it.

**Independent Test**: Ask any journey question and confirm the
response meta carries the model ID, provider, and latency, and
that the same three values appear in the server logs for that
request.

**Acceptance Scenarios**:

1. **Given** any journey-helper response, **When** it is
   delivered, **Then** its meta exposes the model ID, the
   provider, and the latency of the call that produced it.
2. **Given** the same response, **When** a reviewer inspects the
   server logs for that request, **Then** the same model ID,
   provider, and latency are recorded there.
3. **Given** any AI-assisted answer shown in the passenger UI,
   **When** it renders, **Then** it is visually distinct from
   authoritative data and labelled unverified.

---

### Edge Cases

- What happens when the model cannot be reached (declared model
  unavailable, backend SDK error, timeout)? The helper says
  plainly that it cannot answer right now and suggests trying
  again or browsing routes directly — it never falls back to an
  ungrounded answer.
- What happens when the model returns a route the dataset does
  not contain, or a time despite being told not to? The backend
  verification rejects the ungrounded part before delivery: only
  evidence-verified direct connections reach the passenger, and
  anything unverifiable becomes a refusal.
- What happens when the passenger asks for times, transfers, or a
  multi-leg journey? The helper declines that part plainly and
  offers what it can do: direct-service answers from the dataset.
- What happens when the passenger sends an empty question or an
  empty transcript? The helper asks for the journey question
  again instead of calling the model.
- What happens when the same journey is asked twice? Each answer
  is computed fresh from the dataset; no per-user history or
  memory carries over between requests (no tracking, FR-017).
- What happens when the transcript contains personal details the
  passenger dictated? They are used only to answer that request
  and are not stored, logged, or used for any other purpose.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The journey helper MUST call a declared Meta model
  at runtime via a direct backend SDK. The frontend MUST NOT call
  models directly.
- **FR-002**: The model MUST be exposed to the agent through
  exactly three tools: `search_stops` (find stops by name or map
  area), `find_routes` (direct-route connectivity between two
  stops), and `get_route_detail` (ordered stops and evidence for
  one route).
- **FR-003**: All tools MUST be read-only functions over the
  application-owned dataset (the API built in
  `specs/003-read-map-api`). No tool may create, modify, or
  delete any transit data, feedback record, or canonical record.
- **FR-004**: All tools MUST carry explicit JSON schemas, and
  the schemas MUST be MCP-compatible. The MVP MUST NOT stand up a
  separate MCP server (Principle IX).
- **FR-005**: The helper MUST give evidence-verified direct
  connectivity answers only: every cited route MUST be confirmed
  against the dataset (the serving route exists and contains both
  stops in travelling order) before the answer is delivered.
- **FR-006**: Journey answers MUST NOT contain schedules,
  departure or arrival times, durations, frequencies, or transfer
  instructions. A model output containing any of these MUST be
  stripped or refused before delivery, never passed through.
- **FR-007**: When no direct service is known, the helper MUST
  refuse plainly and MUST NOT invent a route, time, or transfer
  to fill the gap.
- **FR-008**: When a journey request names a stop matching more
  than one stop, the helper MUST ask the passenger to choose
  between the candidates and MUST NOT answer the journey until
  the ambiguity is resolved.
- **FR-009**: When a journey request names a stop matching
  nothing, the helper MUST say so plainly and MUST NOT invent a
  stop or silently substitute another one.
- **FR-010**: Every route cited in any answer MUST link to its
  evidence at `/routes/:id`, and every such link MUST resolve to
  an existing route.
- **FR-011**: Voice input MUST go through Muse Voice Transcribe
  as an input mode only: the transcript MUST be shown to the
  passenger and MUST be editable before sending.
- **FR-012**: No audio from voice input may be retained: not on
  the device beyond the session's needs, not on the server, and
  not in any log or analytics store.
- **FR-013**: Every journey-helper response MUST expose the model
  ID, the provider, and the latency of the producing call in its
  response meta.
- **FR-014**: The same model ID, provider, and latency MUST be
  recorded in the server logs for that request.
- **FR-015**: Every AI-assisted answer in the passenger UI MUST
  render distinctly as AI-generated and MUST be labelled
  unverified.
- **FR-016**: The helper MUST NOT mutate canonical data under any
  circumstance: no feedback auto-rejection, no record creation,
  no corrections applied. Moderator triage remains human
  (Principle IX).
- **FR-017**: The helper MUST follow data minimisation: no user
  accounts, no tracking, no per-user memory across requests, and
  no personal data stored or logged. A dictated transcript
  containing personal details is used only for that request.
- **FR-018**: Every backend SDK or model failure (declared model
  unavailable, timeout, malformed model output) MUST surface to
  the passenger as a plain-language cannot-answer-right-now
  message, never as an ungrounded answer or a technical dump.
- **FR-019**: The declared model (model ID and provider) MUST be
  named in the plan so tests and reviewers can verify exactly
  which model was exercised; swapping the declaration is a plan
  change, not a silent substitution.
- **FR-020**: The helper MUST NOT depend on the public Nominatim
  service or any external place search; stop resolution uses the
  application's own stop data (constitution stack constraints).
- **FR-021**: Every journey answer MUST name the resolved boarding
  and alighting stops in plain words alongside the route evidence
  (Story 1/AC5), so the passenger can see what the helper
  understood and catch a misresolution before travelling.
- **FR-022**: The Journey tab MUST offer From and To stop pickers
  that resolve names against the application's own stop data
  and query the public `GET /api/v1/connectivity/` endpoint. A
  picked stop stays shown in its own input with a selected
  style and an inline clear control; typing again clears the
  selection (Story 1/AC6).
- **FR-023**: The Journey panel MUST keep a single shared result
  area for both search modes: starting one search clears the
  other's results and cancels its in-flight request, so only
  one answer is ever visible at a time (Story 1/AC6).

### Key Entities *(include if feature involves data)*

- **Journey Query**: One passenger question (typed or dictated).
  Carries the raw text (or edited transcript) and, after
  resolution, the two resolved stops. Carries no user identity
  and leaves no per-user trace.
- **Agent Tool Call**: One invocation of `search_stops`,
  `find_routes`, or `get_route_detail` by the model. Carries the
  JSON arguments, the read-only result, and the fact that nothing
  was written. Tool definitions carry MCP-compatible JSON schemas.
- **Evidence-Grounded Answer**: One delivered journey answer.
  Carries the cited routes, each with its `/routes/:id` evidence
  link, plus the response meta (model ID, provider, latency) and
  the unverified label. Carries no times and no transfers.
- **Refusal**: One honest non-answer. Carries the plain-language
  reason (unknown connection, ambiguous stop, model
  unavailable) and, where applicable, the disambiguation
  candidates. Nothing unverifiable is delivered alongside it.
- **Transcript**: The editable text produced from voice input.
  Carries only the words to be answered; the audio it came from
  is never retained.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a known set of connected stop pairs, 100% of
  journey answers cite only routes verified in the dataset with
  working `/routes/:id` evidence links, name the resolved
  boarding and alighting stops in plain words (FR-021), and 0%
  contain times, durations, frequencies, or transfer
  instructions.
- **SC-002**: For a known set of unconnected pairs and unknown
  stop names, 100% of responses are plain-language refusals and
  0% invent a route, stop, time, or transfer.
- **SC-003**: For ambiguous stop names with a known candidate
  set, 100% of first responses ask the passenger to choose
  (naming all candidates) and give no journey answer before the
  choice; the follow-up answer meets SC-001 for the chosen stop.
- **SC-004**: In voice-mode checks, 100% of dictations produce an
  editable transcript, the sent answer reflects the edited text
  in 100% of edited cases, and review confirms 0 bytes of audio
  retained on device beyond the session, server, or logs.
- **SC-005**: 100% of journey-helper responses carry model ID,
  provider, and latency in their meta, 100% of the matching log
  entries record the same three values, and 100% of AI-assisted
  UI answers render distinctly labelled unverified.
- **SC-006**: 100% of tool calls observed in tests are reads
  against the application dataset; 0% write, mutate, reject, or
  create any record, and all three tool schemas validate as
  MCP-compatible JSON without a running MCP server.
- **SC-007**: Simulated backend SDK or model failures (declared
  model unreachable, timeout, malformed output, hallucinated
  route) produce the plain-language cannot-answer message in
  100% of cases, with 0 ungrounded answers delivered and 0
  technical error dumps shown to passengers.
- **SC-008**: Review confirms 100% of journey-helper traffic
  passes with no accounts, no tracking, no per-user memory, and
  no personal data in storage or logs, and that no external
  place-search service is called.

## Assumptions

- The read API from `specs/003-read-map-api` (routes, stops,
  connectivity, shared envelope, servable dataset) is the dataset
  surface the tools query; this feature adds no new transit data
  and performs no import.
- The exact declared model (model ID and provider) is named at
  plan time in `research.md` and recorded per FR-019; the spec
  fixes the behaviour contract (evidence-only, refusal,
  transparency), not the model choice.
- Reference documentation for the Meta backend SDK, the Voice
  Transcribe integration, or the model catalogue may be supplied
  by the requester at plan time ("If required I can provide
  reference documentation"); the plan records whichever
  references were used, and behaviour here does not depend on
  them.
- "Direct backend SDK" means server-side calls from
  `backend/` only; the frontend reaches the helper exclusively
  through the versioned REST API (Principles IV and IX).
- Model-failure handling assumes ordinary server logging already
  exists; the model, provider, and latency values are ordinary
  request fields, not a new analytics pipeline (Principle III).
- Voice transcription runs through Muse Voice Transcribe as the
  input mode; transcript editing happens client-side before any
  model call, so unedited dictation audio never needs to leave
  the device for correction.
- AI-assisted answers are labelled unverified even when every
  cited route checks out: verification covers the data, not the
  machine's wording (Principle IX).
- No per-user conversation memory is introduced; each journey
  question is answered from the dataset as it stands at request
  time (FR-017).
- The follow-up passenger-facing description (everyday language
  by text or voice, editable-transcript fallback, ambiguous-stop
  resolution, verified direct routes with stop evidence and route
  links, clear guidance when no direct service exists, no invented
  times/transfers/routes, no data modification, unverified
  informational guidance with human-readable evidence) restates
  the same feature from the passenger's side and is folded into
  this spec as Story 1/AC5, FR-021, and the SC-001 stop-naming
  measure above — no separate spec was created for it.

