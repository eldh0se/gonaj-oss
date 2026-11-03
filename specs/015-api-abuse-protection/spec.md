# Feature Specification: API Abuse Protection

**Feature Branch**: `015-api-abuse-protection`

**Created**: 2026-11-03

**Status**: Draft

**Input**: User description: "Basic abuse protection for open journey and transcribe APIs. Both POST endpoints stay login-free but need bounded cost. What changes: separate per-IP throttle budgets for journey and transcribe, strict request size caps on question history and context, keep 5MB WAV-only transcribe cap, production hardening via env. Why: shared 180/min read budget lets one client burn LLM quota. Out of scope: accounts, API keys, captcha, WAF."

## Clarifications

### Session 2026-11-03

- Q: Should journey and transcribe leave the shared read throttle budgets entirely, or keep counting toward them as a backstop? → A: Fully independent — journey/transcribe leave the shared read budgets entirely; only their own budgets apply.
- Q: When a request is both oversized and over its throttle budget, which rejection should the client receive? → A: Size and shape checks run first — oversized requests get the size error even when throttled; only well-formed requests count toward the budget.
- Q: Should the spec's default budgets and caps stay as written, or be tightened or loosened? → A: Keep the spec defaults — the Assumptions numbers stand as the production starting point, retunable via env per FR-007.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Journey asks stay cheap per client (Priority: P1)

A passenger asks journey questions normally while a different client floods the journey endpoint. The flooder gets throttled; the passenger's asks, stops/routes reads, and voice uploads keep working because the journey endpoint has its own per-client budget instead of sharing the general read budget.

**Why this priority**: The journey endpoint burns model quota per call. Sharing the 180/min read budget means one abusive client can exhaust LLM quota for everyone. A dedicated per-client budget bounds that cost without logins.

**Independent Test**: Send journey asks from two client identities; drive one past its budget and confirm it receives throttled responses while the other client's asks still succeed.

**Acceptance Scenarios**:

1. **Given** a client under its journey budget, **When** it asks a journey question, **Then** the request is served normally with no throttle headers blocking it.
2. **Given** a client that exceeded its journey per-minute budget, **When** it asks again within the same window, **Then** it receives a throttled response telling it to retry later, and no model call is consumed.
3. **Given** a throttled journey client, **When** a different client asks or reads stops/routes, **Then** those requests succeed — budgets are per client and per endpoint.

---

### User Story 2 - Voice uploads stay cheap per client (Priority: P2)

A passenger dictates a journey question while a different client floods the transcribe endpoint with audio. The flooder gets throttled under a budget sized for audio-plus-model cost; the passenger's dictation and everyone else's journey asks keep working because transcribe has its own per-client budget.

**Why this priority**: Each transcribe call costs audio ingress plus model inference — the most expensive request in the product. It must not share a budget with cheap reads or with text asks.

**Independent Test**: Send transcribe uploads from two client identities; drive one past its budget and confirm it is throttled while the other client's uploads and journey asks still succeed.

**Acceptance Scenarios**:

1. **Given** a client under its transcribe budget, **When** it uploads a valid WAV, **Then** the transcript returns normally.
2. **Given** a client that exceeded its transcribe per-minute budget, **When** it uploads again within the same window, **Then** it receives a throttled response telling it to retry later, and no transcription cost is consumed.
3. **Given** a throttled transcribe client, **When** any client asks a journey question, **Then** the ask succeeds — transcribe and journey budgets are independent.

---

### User Story 3 - Oversized payloads fail fast without model cost (Priority: P2)

A client sends a journey ask with a huge question, a long conversation history, or a bloated context object. The API rejects it immediately with a plain-language size error before any model call, so giant payloads cannot burn quota or slow the service.

**Why this priority**: Without caps, history and context are unbounded arrays the client controls; each extra turn multiplies model cost. Caps make the worst-case cost per request predictable.

**Independent Test**: POST journey asks with an over-long question, an over-long history, and an over-long context in turn; confirm each is rejected with a size error and no model call runs.

**Acceptance Scenarios**:

1. **Given** a question longer than the question cap, **When** it is asked, **Then** it is rejected with a plain-language size error and no model call runs.
2. **Given** a history longer than the history cap (too many turns or an over-long turn), **When** it is sent, **Then** it is rejected with a plain-language size error and no model call runs.
3. **Given** a context object bigger than the context cap, **When** it is sent, **Then** it is rejected with a plain-language size error and no model call runs.
4. **Given** a non-WAV upload or one larger than 5MB, **When** it is transcribed, **Then** the existing WAV-only 5MB rejection applies unchanged.

---

### Edge Cases

- Throttled responses carry a `Retry-After` hint and a plain-language message consistent with existing API errors; the throttled request never reaches the model or transcriber.
- A client behind NAT shares its budget with whoever shares its public IP — accepted limitation, not solved (accounts are out of scope).
- Deployments behind a reverse proxy keep identifying clients by forwarded address only when explicitly configured to trust the proxy (existing behavior).
- Missing or empty tuning values fall back to safe compiled-in defaults; the service never starts with an unbounded budget.
- Legitimate burst use (a few quick asks, one dictation) never hits any budget — budgets allow normal human pace with headroom.
- Size caps apply before authentication-free model work but after basic shape validation, so malformed requests still get the existing shape errors.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The journey ask endpoint MUST have its own per-client throttle budget (per-minute and per-day), fully independent of the general read budget and of transcribe: journey calls MUST NOT count toward the general read budgets.
- **FR-002**: The transcribe endpoint MUST have its own per-client throttle budget (per-minute and per-day), fully independent of the general read budget and of journey (transcribe calls MUST NOT count toward the general read budgets), sized tighter to reflect audio-plus-model cost.
- **FR-003**: Throttle identity MUST stay per client IP using the existing hashed-counter scheme (no raw IPs stored); proxy deployments MUST keep honoring the explicit trusted-proxy setting and nothing else.
- **FR-004**: Throttled requests MUST fail with HTTP 429 plus a `Retry-After` hint and a plain-language retry message, and MUST NOT consume model or transcription quota. Size and shape checks run before the throttle check, so an oversized request gets the size error even when the client is over budget.
- **FR-005**: Journey asks MUST enforce size caps: question text at most 500 characters, history at most 10 turns with each turn at most 500 characters, context at most 8KB serialized. Oversized requests MUST be rejected with a plain-language size error before any model call, and rejected requests MUST NOT count toward the throttle budget — only well-formed requests consume budget.
- **FR-006**: Transcribe MUST keep the existing WAV-only 5MB upload cap unchanged, enforced under its own budget.
- **FR-007**: Every budget and cap MUST be overridable via environment variables with safe compiled-in defaults, so production tuning needs no code change.
- **FR-008**: Both endpoints MUST stay login-free with no accounts, API keys, captchas, or WAF — abuse control is budgets and caps only.

### Key Entities

- **ThrottleBudget**: A named per-endpoint, per-client allowance — which endpoint, how many requests per minute and per day, keyed by hashed client IP.
- **RequestCaps**: The size envelope for a request — max question length, max history turns and turn length, max serialized context size, max audio bytes and allowed audio type.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: One client flooding journey asks receives throttled responses while a second client's asks and map reads succeed normally throughout.
- **SC-002**: One client flooding voice uploads receives throttled responses while a second client's uploads and journey asks succeed normally throughout.
- **SC-003**: An ask with an over-long question, history, or context is rejected with a size error and triggers zero model calls.
- **SC-004**: Operators can tighten or loosen any budget or cap through environment configuration alone, with no code change and no restart beyond the normal deploy.

## Assumptions

- Default budgets (tunable via env, confirmed 2026-11-03): journey 60/min and 1500/day per client; transcribe 20/min and 300/day per client. These bound worst-case model cost while leaving normal human pace (a few asks or dictations per minute) untouched.
- Default caps (tunable via env): question 500 chars, history 10 turns × 500 chars per turn, context 8KB serialized. Current legitimate clients (typed questions, empty/short histories, small selection contexts) fit comfortably inside.
- The existing general read budget (180/min, 5000/day) and day-budget mechanics are unchanged; journey and transcribe simply stop sharing them.
- Throttled and oversized responses follow the existing plain-language JSON error style with HTTP 429 for throttles and 400 for size violations.
- Counter storage reuses the existing hashed-IP expiring-counter mechanism; no new infrastructure.
- Per-IP limiting is best-effort under NAT/CGNAT: heavy sharers of one public IP share one budget. Accounts or device attestation would fix that and are explicitly out of scope.
