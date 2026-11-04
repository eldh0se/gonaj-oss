# Feature Specification: Anonymous Passenger Feedback

**Feature Branch**: `017-anonymous-feedback`

**Created**: 2026-11-04

**Status**: Draft

**Input**: User description: "Anonymous passenger feedback for single-page transport map. Goal: Let passengers report incorrect, missing, or outdated routes/stops and journey from/to mismatches to support human curation. No accounts, no tracking, no canonical data mutation. Entry points on single MapPage: RouteOverlay Report issue, Stop card Report issue, Journey result Report issue, generic header Report issue. All open one dialog; no new page or route; map state preserved. Dialog behavior: Prefill route/stop/journey context where available as editable removable chips backed by existing route/stop search. Allow general feedback with no context. Require category incorrect|missing|outdated|other and message 1-2000 chars after strip. Block duplicate submit while pending. Handle loading, validation, 400, 429, and error with retry. Backend: New FeedbackReport with reference FB-XXXXXXXX unique receipt-only, category, message, optional route FK SET_NULL, optional stop FK SET_NULL, status new|reviewed|dismissed default new, created_at/updated_at. Journey from/to carried as structured text in message; no journey schema change. Public POST /api/v1/feedback/ returns 201 reference plus unverified receipt; unknown route_id/stop_id returns 400 invalid-reference, never 500; non-writable reference/status/timestamps return 400 if supplied; reuse existing IP throttling; return 429 with Retry-After. Review via Django Admin only; no public listing; no admin REST in scope. Receipt: Show reference only plus text: received not verified, anonymous with no tracking, save reference for records, no lookup. Non-goals: No login, no attachments, no auto-moderation, no AI categorization, no verification workflow, no canonical Route/Stop writes." Goal: Let passengers report incorrect, missing, or outdated routes/stops and journey from/to mismatches to support human curation. No accounts, no tracking, no canonical data mutation. Entry points on single MapPage: RouteOverlay Report issue, Stop card Report issue, Journey result Report issue, generic header Report issue. All open one dialog; no new page or route; map state preserved. Dialog behavior: Prefill route/stop/journey context where available as removable chips; no in-dialog search. Allow general feedback with no context. Require category incorrect|missing|outdated|other and message 1-2000 chars after strip. Block duplicate submit while pending. Handle loading, validation, 400, 429, and error with retry. Backend: New FeedbackReport with reference FB-XXXXXXXX unique receipt-only, category, message, optional route FK SET_NULL, optional stop FK SET_NULL, status new|reviewed|dismissed default new, created_at/updated_at. Journey from/to carried as structured text in message; no journey schema change. Public POST /api/v1/feedback/ returns 201 reference plus unverified receipt; unknown route_id/stop_id returns 400 invalid-reference, never 500; non-writable reference/status/timestamps return 400 if supplied; reuse existing IP throttling; return 429 with Retry-After. Review via Django Admin only; no public listing; no admin REST in scope. Receipt: Show reference only plus text: received not verified, anonymous with no tracking, save reference for records, no lookup. Non-goals: No login, no attachments, no auto-moderation, no AI categorization, no verification workflow, no canonical Route/Stop writes."

## Clarifications

### Session 2026-11-04

- Q: Journey encoding — FR-007 says ends travel inside the message while data-model composes the header server-side; which side defines the fields? → A: Contract defines separate `journey`/`from_name`/`to_name`/`question` input fields; the server embeds them as the stored header. FR-007 reworded to match; no frontend/backend mismatch.
- Q: Does the 1–2000 limit cover the total stored text or the user message? → A: User-typed message only; the server-composed journey header is excluded. One rule, in FR-003 and the contract.
- Q: Is removing reviewed↔dismissed re-triage intentional? → A: No — re-triage is restored (`new` → `reviewed`|`dismissed` plus `reviewed` ↔ `dismissed`, Admin only).
- Q: Is dropping the status/created_at index intentional? → A: No — composite `(status, created_at)` index added for the curator queue.
- Q: Do feedback reports share journey/transcribe throttle budgets? → A: No — dedicated `feedback_min`/`feedback_day` budgets (defaults 20/min, 100/day); only the machinery and cache are reused. Assumption updated to match the plan.
- Q: SC-005 "with no code changes" vs the new FeedbackReportAdmin — what is meant? → A: No new tooling beyond Admin configuration; SC-005 rephrased accordingly.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Report an issue about what I'm looking at (Priority: P1)

A passenger viewing a route overlay, a stop card, or a journey answer spots something wrong and taps Report issue. One dialog opens over the unchanged map; the route, stop, or journey ends are already attached as removable chips. The passenger picks a category, types what is wrong, submits, and gets a reference receipt. The map behind the dialog never moves and nothing else on the page changes.

**Why this priority**: Contextual reporting is the whole value — a report without its route/stop context is far less actionable for curators, and every extra step loses reports.

**Independent Test**: Open each of the three contextual entry points, confirm the dialog prefills the right chip, submit a valid report, and confirm the receipt shows the reference while the map state is untouched.

**Acceptance Scenarios**:

1. **Given** an open route overlay, **When** the passenger taps Report issue, **Then** one dialog opens with the route attached as a chip and the map state unchanged behind it.
2. **Given** an open stop card, **When** the passenger taps Report issue, **Then** the dialog opens with that stop attached as a chip.
3. **Given** a journey answer, **When** the passenger taps Report issue, **Then** the dialog opens with the journey ends attached and the question preserved.
4. **Given** a filled dialog, **When** the passenger submits, **Then** exactly one record is created, the dialog shows the reference receipt, and closing it returns to the unchanged map.

---

### User Story 2 - Report a general issue with no context (Priority: P1)

A passenger notices a problem that is not tied to anything on screen (or starts from the header) and taps Report issue. The same dialog opens with no chips; the passenger files it general and gets the same receipt.

**Why this priority**: Many real reports (a missing stop, a wrong name seen offline) start with no context on screen; without this path those reports are lost.

**Independent Test**: Open the header entry point with an empty map context, file one report with no chips, and confirm the receipt.

**Acceptance Scenarios**:

1. **Given** the header Report issue entry, **When** the passenger opens it, **Then** the same dialog opens with no chips and the map unchanged.
2. **Given** a contextual dialog, **When** the passenger removes a prefilled chip, **Then** submission proceeds without that context.

---

### User Story 3 - Curator triages reports without code changes (Priority: P2)

A curator opens the existing internal review interface, sees new reports with their reference, category, message, linked route/stop, and timestamps, and marks each reviewed or dismissed. Passengers never see this list and no new internal tooling is built.

**Why this priority**: Reports nobody reads are worse than no reports; the human-curation loop is the stated goal, served through the existing interface.

**Independent Test**: File reports covering every category and status transition, and confirm each appears in the review interface with its context and can move from new to reviewed or dismissed.

**Acceptance Scenarios**:

1. **Given** submitted reports, **When** a curator opens the review interface, **Then** each shows reference, category, message, linked route/stop names, status, and timestamps.
2. **Given** a new report, **When** the curator marks it reviewed or dismissed, **Then** the status persists and the report leaves the new queue.

---

### User Story 4 - Failed or abusive submissions fail plainly (Priority: P2)

A passenger submits with an empty message, an over-long message, a stale route reference, no network, or too many attempts in a row. Each case gets a plain-language explanation in the dialog — what was wrong, or that the service is busy with a retry path — and never a dead end or a duplicate record.

**Why this priority**: Anonymous endpoints attract garbage and honest mistakes alike; clear rejection keeps the queue usable and the experience trustworthy.

**Independent Test**: Drive each failure (empty/whitespace message, 2001-char message, unknown route/stop id, forced 429, forced 500/network drop, double-tap submit) and confirm the dialog message, the single-record guarantee, and the retry path.

**Acceptance Scenarios**:

1. **Given** an empty or whitespace-only message, **When** the passenger submits, **Then** the dialog explains a message is required and nothing is sent.
2. **Given** a 2001-character message, **When** the passenger submits, **Then** the dialog explains the 2000-character limit.
3. **Given** a route or stop that no longer exists, **When** the passenger submits, **Then** the dialog explains the reference is invalid and no server error surfaces.
4. **Given** a throttled client, **When** the passenger submits, **Then** the dialog explains the service is busy with when to retry.
5. **Given** a pending submission, **When** the passenger taps submit again, **Then** no second record is created.

---

### Edge Cases

- Message of only whitespace counts as empty; exactly 2000 characters is accepted, 2001 is rejected.
- A route or stop deleted between chip attach and submit submits as invalid-reference (400), never a server error; records keep working when the linked route/stop is later deleted (link clears, record stays).
- Closing the dialog mid-submit leaves the single in-flight request alone; reopening starts a fresh draft, never a duplicate.
- Network failure keeps the draft text in the dialog with a retry path.
- Message content with markup or special characters is stored verbatim and rendered safely in the review interface.
- Journey context where either end failed to resolve attaches whatever ends are known, or nothing, and still submits.
- A response that supplies reference, status, or timestamps is rejected as invalid input.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Four entry points (route overlay, stop card, journey result, generic header) MUST open one shared report dialog; no new page or route is added and map state MUST be preserved behind it.
- **FR-002**: The dialog MUST prefill route/stop/journey context as removable chips from the entry context (no in-dialog search), and MUST accept general feedback with no chips attached.
- **FR-003**: Submission MUST require a category of incorrect, missing, outdated, or other, and a user-typed message of 1–2000 characters after stripping whitespace (the limit applies to the user message; the server-composed journey header is excluded).
- **FR-004**: The dialog MUST block duplicate submission while a request is pending (at most one record per user submit).
- **FR-005**: The dialog MUST handle loading, client validation, 400, 429, and other errors with plain-language messages and a retry path that preserves the draft.
- **FR-006**: The backend MUST persist a FeedbackReport with a unique receipt-only reference of the form FB-XXXXXXXX, category, message, optional route link (cleared if the route is deleted), optional stop link (cleared if the stop is deleted), status of new, reviewed, or dismissed defaulting to new, and creation/update timestamps.
- **FR-007**: Journey from/to context MUST be sent as a separate journey object (`from_name`, `to_name`, `question` per the contract); the server embeds it as a structured text header inside the stored message; no journey-side schema change is made.
- **FR-008**: Public POST /api/v1/feedback/ MUST return 201 with the reference plus an unverified receipt on success; unknown route/stop ids MUST return 400 invalid-reference and never 500; supplied reference, status, or timestamps MUST return 400; per-IP throttling MUST be reused with 429 plus Retry-After.
- **FR-009**: The receipt MUST show the reference only, plus text stating the report is received but not verified, that reporting is anonymous with no tracking, and that the passenger should save the reference for their records because there is no lookup.
- **FR-010**: Review MUST happen through the existing internal review interface only; no public listing of reports and no new admin REST surface are in scope.

### Key Entities

- **FeedbackReport**: A passenger's report — unique receipt reference, category, message (embedding any journey ends as text), optional links to one route and one stop that clear on deletion, review status, timestamps. Never modified by public endpoints after creation.
- **ReportChip**: Transient dialog attachment — a route, stop, or journey end prefilled from the entry context that the passenger can remove before submitting; carries no persistence of its own.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A passenger can file a contextual report from any of the four entry points in under 2 minutes with the map state unchanged.
- **SC-002**: Every valid submission returns a reference receipt, and every invalid reference is rejected with a plain client error — zero server errors from malformed input.
- **SC-003**: Double submit taps while a request is pending never create a second record.
- **SC-004**: Throttled submitters receive a busy explanation with retry guidance instead of a silent failure.
- **SC-005**: A curator can list, filter, and resolve every submitted report using only the existing internal review interface (no new tooling beyond Admin configuration).

## Assumptions

- The four request categories (incorrect, missing, outdated, other) are used as specified; alignment with the constitution's feedback-category vocabulary, if any gap is found, is resolved at plan time without changing the public contract.
- Reference format is FB- followed by 8 uppercase alphanumerics, generated server-side and never accepted from clients.
- Per-IP throttling reuses the existing throttle machinery and cache with dedicated `feedback_min`/`feedback_day` budgets (defaults 20/min, 100/day, env-overridable); it does not share the journey/transcribe budget values.
- Chip search reuses the existing public route/stop search endpoints with no new search API.
- There is no reference lookup endpoint by design; "save your reference" is the whole retrieval story.
