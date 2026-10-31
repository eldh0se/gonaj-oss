# Feature Specification: Journey Selection Resolve

**Feature Branch**: `008-journey-selection-resolve`

**Created**: 2026-10-31

**Status**: Draft

**Input**: User description: "Feature/fix 008: journey selection must resolve after the passenger picks a stop. Passengers asking `Aluva to Kaloor` see several same-named stops and pick one, but get asked again indefinitely. Both ends can be ambiguous, and same-road opposite-side duplicates are normal. What changes: picking a candidate advances the journey toward a verified answer or honest refusal, never a repeat of the same prompt. Invalid picks refuse safely. All answers stay evidence-linked with no times or transfers. Why: without this, the helper cannot serve unfamiliar users, the primary audience."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Pick a stop once and get an answer or honest refusal (Priority: P1)

A passenger unfamiliar with Kochi asks for a journey such as "Aluva to Kaloor". The helper finds several same-named stops and shows a candidate list. The passenger picks one candidate (for example by choosing it from the list or naming it unambiguously). The journey then advances: the helper either gives the verified journey answer for the chosen stop or honestly refuses because it cannot verify one — it never asks the passenger to pick the same stop again.

**Why this priority**: This is the reported defect. Unfamiliar users are the primary audience, and an indefinite repeat prompt makes the helper unusable for them. Fixing single-end selection restores the core "how do I get from A to B" journey.

**Independent Test**: Ask a journey question with one ambiguous end, receive the candidate list, pick one valid candidate, and confirm the next response is either a verified journey answer or a refusal — never a repeat of the same candidate prompt.

**Acceptance Scenarios**:

1. **Given** the helper has shown a candidate list for one ambiguous stop name, **When** the passenger picks exactly one listed candidate, **Then** the next response is either a verified journey answer for the chosen stop or an honest refusal, and it is not a repeat of the same candidate prompt.
2. **Given** the helper has shown a candidate list, **When** the passenger picks a candidate and a verified direct connection exists for the resolved journey, **Then** the answer names the resolved stops and links each cited route to its evidence.
3. **Given** the helper has shown a candidate list, **When** the passenger picks a candidate and no direct connection can be verified for the resolved journey, **Then** the helper honestly refuses (for example, states no direct service was found or the place is unknown) instead of repeating the prompt or inventing an answer.

---

### User Story 2 - Resolve both ends when both are ambiguous (Priority: P1)

A passenger asks a journey where both the origin and the destination are ambiguous (for example "Aluva to Kaloor" where each name matches several stops). The helper resolves one end at a time: after the passenger picks a candidate for the first end, the helper keeps that choice and asks only about the still-unresolved end, then advances to a verified answer or honest refusal once both ends are resolved.

**Why this priority**: The defect report explicitly calls out that both ends can be ambiguous. Resolving only one end leaves the reported "Aluva to Kaloor" case broken.

**Independent Test**: Ask a journey question with both ends ambiguous, pick a candidate for the first end, confirm the helper retains that pick and prompts only for the remaining end, then pick the second candidate and confirm the outcome is a verified answer or honest refusal.

**Acceptance Scenarios**:

1. **Given** both journey ends are ambiguous, **When** the passenger picks a valid candidate for the first prompted end, **Then** the helper retains that pick and prompts only for the still-unresolved end rather than repeating the first prompt or dropping the first pick.
2. **Given** the first end has been picked and only the second end remains ambiguous, **When** the passenger picks a valid candidate for the second end, **Then** the helper gives a verified journey answer for the fully resolved journey or honestly refuses.
3. **Given** a two-ended ambiguous journey, **When** the passenger resolves both ends through successive picks, **Then** the whole exchange completes without ever re-asking an already-resolved end with an identical prompt.

---

### User Story 3 - Invalid picks fail safely without inventing a journey (Priority: P2)

A passenger replies to a candidate prompt with something that does not identify a listed candidate (for example a made-up place, a number or name that matches nothing on the list, or a gibberish reply). The helper refuses safely: it explains it could not match the pick, does not invent a stop or a journey, and does not crash or loop the identical prompt indefinitely.

**Why this priority**: Safe refusal is the constitution-mandated fallback (refuse when unknown). Without it, invalid input could produce invented journeys or a second infinite loop.

**Independent Test**: Trigger a candidate prompt, reply with an invalid pick, and confirm the response is a safe refusal that names the problem and offers a bounded next step (such as rephrasing) rather than a journey answer or an identical repeated prompt.

**Acceptance Scenarios**:

1. **Given** a candidate prompt is pending, **When** the passenger replies with a pick that matches none of the listed candidates, **Then** the helper refuses safely by stating it could not match the pick and does not present an invented journey.
2. **Given** a candidate prompt is pending, **When** the passenger replies with an empty or incomprehensible message, **Then** the helper responds with a safe refusal or a guided re-prompt that differs from a bare repeat (for example, restating what a valid pick looks like) and never invents stops or routes.

---

### Edge Cases

- Same-road opposite-side duplicates: two stops share a name because they serve opposite sides of the same road. Picking either one MUST advance the journey normally; the pair MUST NOT be treated as an error or force an extra confirmation loop.
- Pick expressed by position, exact name, or visible choice: any reply that unambiguously identifies exactly one listed candidate counts as a valid pick; a reply that matches zero or more than one listed candidate counts as invalid.
- Both ends resolve to stops with no verified direct connection: the helper refuses honestly (no direct service found) rather than re-prompting.
- Passenger changes the subject instead of picking (asks a new journey question): the new question starts fresh; the old pending candidate list MUST NOT leak into the new answer.
- Repeated invalid picks: each invalid reply still refuses safely and MUST NOT produce an unbounded identical-prompt loop.
- Evidence and content rules still hold after selection: every cited route links to its evidence; answers contain no times and no transfers.
- Candidate list shown to the passenger always identifies each option distinctly enough to pick (name plus distinguishing detail where duplicates share a name).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: After showing a stop-candidate prompt, the helper MUST treat any reply that unambiguously identifies exactly one listed candidate as a valid pick that advances the journey.
- **FR-002**: A valid pick MUST advance the journey to exactly one of: (a) a verified journey answer for the resolved stop(s), (b) a prompt for the remaining unresolved end only, or (c) an honest refusal. It MUST NEVER return the identical candidate prompt for the already-picked stop.
- **FR-003**: When both journey ends are ambiguous, the helper MUST resolve them independently: a valid pick for one end MUST be retained while the other end is resolved, and an already-resolved end MUST NOT be re-prompted with the same candidates.
- **FR-004**: Same-road opposite-side duplicate stops MUST be treated as ordinary distinct candidates; picking either one MUST advance the journey under FR-002 with no extra mandatory confirmation step.
- **FR-005**: A reply that matches zero listed candidates, or that matches more than one listed candidate ambiguously, MUST be treated as an invalid pick and MUST receive a safe refusal that states the pick could not be matched and offers a bounded next step (for example, rephrase or choose from the list). It MUST NOT produce an invented stop, route, or journey.
- **FR-006**: Resolution MUST NOT depend on the passenger repeating the original full journey question; the pending candidate context MUST carry forward so the pick alone is sufficient to advance.
- **FR-007**: Every journey answer given after selection MUST remain evidence-linked: each cited route MUST link to its evidence, and the answer MUST identify the resolved origin and destination stops used.
- **FR-008**: Every journey answer given after selection MUST contain no times and no transfers (direct connectivity only), identical to the pre-selection answer rules.
- **FR-009**: When no direct connection can be verified for the resolved stop pair, or a named place matches nothing known, the helper MUST refuse honestly (unknown place / no direct service / cannot verify) instead of repeating the candidate prompt or inventing an answer.
- **FR-010**: A new journey question asked while a candidate prompt is pending MUST start a fresh resolution; the stale candidate list MUST NOT influence the new answer.

### Key Entities

- **Journey request**: A passenger's origin-to-destination question. Has two ends (origin, destination), each of which may be resolved to a single known stop or remain ambiguous.
- **Stop candidate**: One known stop offered as a possible match for an ambiguous end. Has an identity, a display name, and distinguishing detail sufficient to tell same-named stops apart.
- **Disambiguation prompt**: The helper's request to pick from a candidate list for one unresolved end. Advances on a valid pick; never repeats identically after one.
- **Resolved journey**: A journey whose origin and destination each map to exactly one known stop chosen from (or without need of) candidate lists.
- **Verified answer**: A direct-connectivity answer for a resolved journey in which every cited route is verified against evidence and linked to it, with no times or transfers.
- **Honest refusal**: A response stating the helper cannot answer (unknown place, no direct service, unmatched pick, cannot verify), with no invented stops or routes and a bounded next step where applicable.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A passenger who makes a valid pick from a candidate list receives either a verified journey answer or an honest refusal on the next turn — the same candidate prompt is never repeated after a valid pick.
- **SC-002**: Journeys with both ends ambiguous complete within two valid picks: after the first valid pick the helper retains it and prompts only for the remaining end, and after the second valid pick it gives a verified answer or honest refusal.
- **SC-003**: Every reply that matches no listed candidate receives a safe refusal with no invented stop, route, or journey.
- **SC-004**: Every journey answer given after selection links each cited route to its evidence and contains no times and no transfers.
- **SC-005**: Unfamiliar users completing the pick flow succeed without assistance: 9 out of 10 trial journeys with at least one ambiguous end reach a verified answer or honest refusal within two picks per ambiguous end, with no repeated identical prompt observed.

## Assumptions

- Passengers are unfamiliar with exact stop names; same-named stops and same-road opposite-side duplicates are normal data, not data errors.
- A "pick" may arrive as choosing a visible option or as a typed reply (number, exact name, or other unambiguous reference); matching is by unambiguous identification of one listed candidate, not by a single input modality.
- Existing answer rules are unchanged: evidence-linked direct connectivity only, no times, no transfers, honest refusal when unverifiable.
- Existing response metadata and AI-generated rendering rules are unchanged by this fix.
- No schedule data is introduced by this fix; schedule-gated features remain deferred per the constitution.
- Scope is the selection-resolution behavior only; stop search ranking, map rendering, and data corrections are out of scope unless required to distinguish same-named candidates.
