# Feature Specification: Ranked Journey Options

**Feature Branch**: `010-ranked-options`

**Created**: 2026-10-31

**Status**: Draft

**Input**: User description: "Feature 010: answer with ranked options, not one truth. Unfamiliar users need boarding guidance. What changes: helper returns all verified direct options grouped by operator, with boarding hint only when dataset supports it, and destination options within the place region. Never invent stands, times, or transfers. Why: single-answer forces guessing."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See every verified option grouped by operator (Priority: P1)

A passenger unfamiliar with Kochi asks how to get from A to B where several direct services run. Instead of one answer that forces guessing, the helper returns all verified direct options grouped by operator, each naming its boarding and alighting stops and linking its evidence.

**Why this priority**: Single-answer forces guessing; the full verified choice set is the core fix.

**Independent Test**: Ask a journey served by several direct routes; confirm the answer lists every verified option grouped by operator with evidence links, not a single route.

**Acceptance Scenarios**:

1. **Given** several direct services connect the resolved stops, **When** the passenger asks, **Then** the answer lists every verified option grouped by operator.
2. **Given** options are listed, **When** the passenger reads them, **Then** each option names its boarding stop, alighting stop, and evidence link.
3. **Given** the data is unchanged, **When** the same journey is asked twice, **Then** the options appear in the same order both times.

---

### User Story 2 - Boarding guidance only when the data supports it (Priority: P1)

A passenger who does not know where to stand needs boarding guidance. The helper shows a boarding hint (which stop or side to board at) only when the dataset supports it; where it does not, no hint appears — a stand is never invented.

**Why this priority**: Wrong boarding guidance strands unfamiliar users; invented stands are worse than none.

**Independent Test**: Ask journeys with and without hint-supporting data; confirm hints appear exactly where supported and never elsewhere.

**Acceptance Scenarios**:

1. **Given** the dataset supports a boarding hint for an option, **When** the answer is given, **Then** the hint names the boarding point.
2. **Given** the dataset does not support a boarding hint, **When** the answer is given, **Then** no hint appears and no stand is invented.

---

### User Story 3 - Destination options within the place region (Priority: P2)

A passenger heading to a place with several stops (for example any `Kaloor` boarding point) receives the reachable destination options within that place region instead of one forced stop.

**Why this priority**: Forcing one member stop reintroduces the guessing this feature removes; the reachable set lets the passenger match their real destination.

**Independent Test**: Ask a journey into a multi-stop place; confirm the answer offers each reachable member stop and resolves onward travel from the picked one.

**Acceptance Scenarios**:

1. **Given** the destination place has several member stops, **When** direct services reach more than one of them, **Then** the answer offers each reachable member.
2. **Given** the passenger picks one destination member, **When** the journey continues, **Then** it uses that exact member stop.

---

### Edge Cases

- Exactly one verified option: the answer is a one-item list; the helper MUST NOT invent extra options to look ranked.
- No verified option: honest refusal exactly as today (unknown place / no direct service / cannot verify), never a guessed option.
- Operator unknown: options with no known operator appear in a plainly labelled group rather than being dropped or misattributed.
- Hint data missing for some options: hinted and unhinted options coexist; absence of a hint never blocks the option.
- Times, durations, frequencies, transfers: never appear in any option or hint, even when only one option exists.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Journey answers MUST list all verified direct options, not a single route.
- **FR-002**: Options MUST be grouped by operator.
- **FR-003**: Option order MUST be deterministic: the same journey against unchanged data MUST return options in the same order.
- **FR-004**: Every listed option MUST name its boarding stop and alighting stop and link its evidence.
- **FR-005**: A boarding hint MUST appear only where the dataset supports it; stands MUST never be invented.
- **FR-006**: When the destination is a place with several member stops, the answer MUST offer each reachable member instead of forcing one.
- **FR-007**: Answers MUST contain no times, durations, frequencies, or transfers.
- **FR-008**: When nothing is verifiable, the helper MUST refuse honestly instead of listing a guessed option.
- **FR-009**: A single verified option MUST be returned as a one-item list with no invented companions.

### Key Entities

- **Ranked option**: One verified direct service for the journey. Has the route, operator, boarding stop, alighting stop, evidence link, and an optional boarding hint.
- **Operator group**: All options run by one operator, shown together under that operator's name; options with no known operator form a plainly labelled group.
- **Boarding hint**: Guidance on where to board, shown only when dataset-supported and never invented.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Journeys with 3 or more verified direct services list every option grouped by operator with evidence links.
- **SC-002**: 9 out of 10 trial unfamiliar passengers board at the right point on the first try when a boarding hint is shown.
- **SC-003**: Trial audits find zero invented stands, times, or transfers across all answers.
- **SC-004**: Destination-place queries offer every reachable member stop; no trial resolves to a forced single member.

## Assumptions

- Operator names come from the canonical dataset; unknown operators group plainly rather than blocking the answer.
- Whether a boarding hint is supported depends on dataset fields available at plan time; the exact hint source is a planning-time decision recorded in the plan.
- Ranking order is deterministic for unchanged data; the exact ordering key is a planning-time decision.
- Schedule data remains gated per the constitution; nothing here introduces times or timetables.
- The product stays read-only with no accounts and no per-user memory; option lists are computed per request.
