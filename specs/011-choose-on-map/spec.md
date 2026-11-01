# Feature Specification: Choose on the Map

**Feature Branch**: `011-choose-on-map`

**Created**: 2026-10-31

**Status**: Draft

**Input**: User description: "Feature 011: choose on the map. Text lists cannot disambiguate side-of-road stops. What changes: disambiguate auto pans plus zooms to candidate bbox, highlights pins, allows `none of these` plus retry. Users may decline map help. Why: familiar users type IDs, unfamiliar users need geography."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Map moves to the candidates (Priority: P1)

A passenger unfamiliar with Kochi faces a stop-name choice (for example two same-named `Kaloor` stops on opposite sides of the road). When the choice appears, the map automatically pans and zooms so every candidate pin is in view, and the candidate pins are highlighted distinctly from ordinary stops.

**Why this priority**: Text lists cannot convey side-of-road geography; seeing the pins is what makes the choice possible.

**Independent Test**: Trigger a multi-candidate prompt and confirm the map viewport fits every candidate pin on first display, with candidates visually distinct from ordinary stops.

**Acceptance Scenarios**:

1. **Given** a candidate choice is shown, **When** it first appears, **Then** the map viewport fits every candidate pin without manual panning.
2. **Given** candidate pins are in view, **When** the passenger looks at the map, **Then** candidates are highlighted distinctly from ordinary stops.

---

### User Story 2 - Pick a pin or answer none of these (Priority: P1)

The passenger either taps a candidate pin — resolving to that exact stop — or answers `none of these`, which triggers a guided retry (for example rephrasing help or a re-listed choice) instead of a dead end.

**Why this priority**: A tap is the fastest correct resolution; an honest `none of these` path keeps wrong guesses out of the journey.

**Independent Test**: Tap a candidate pin and confirm exact-stop resolution; separately answer `none of these` and confirm a guided retry rather than a dead end or an invented journey.

**Acceptance Scenarios**:

1. **Given** highlighted candidate pins, **When** the passenger picks one pin, **Then** the journey continues from that exact stop.
2. **Given** the candidates are all wrong, **When** the passenger answers `none of these`, **Then** the helper offers a guided retry and never invents a stop or journey.

---

### User Story 3 - Dismiss map help and continue by text (Priority: P2)

Any passenger — familiar or not — may dismiss the map help and continue with the text list alone; the dismissal is respected and the journey still completes. (Familiar users who already know their exact stops may also skip agent search entirely and use direct search; the map helper is for the choosing moment, not a user type.)

**Why this priority**: Map help appears automatically for every same-name list, so declining must always be available; forcing map interaction would break the currently working text flow for anyone who prefers typing.

**Independent Test**: Dismiss map help during a candidate choice and confirm the text list alone completes the journey with no map re-prompts.

**Acceptance Scenarios**:

1. **Given** a candidate choice with map help, **When** the passenger declines it, **Then** the text list remains fully usable and no map prompt reappears for that exchange.
2. **Given** map help is declined, **When** the passenger picks from the text list, **Then** the journey resolves exactly as if the map had never appeared.

---

### Edge Cases

- Single candidate: no choice is needed; the map may show the stop without demanding a pick.
- Map tiles unavailable: the choice degrades silently to the text list with no error blocking the passenger.
- Candidates far apart: the viewport fits all of them even when that means zooming out.
- Repeated `none of these`: each answer receives a guided re-prompt that differs from a bare repeat, never an unbounded identical loop.
- Keyboard and screen-reader use: every candidate pin remains reachable through the text list with identical outcomes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Showing a candidate choice MUST move the map viewport to fit every candidate pin (pan plus zoom) on first display. The map helper appears automatically for every same-name candidate list, for all users — it is never reserved for unfamiliar users only.
- **FR-002**: Candidate pins MUST be highlighted distinctly from ordinary stops while the choice is pending.
- **FR-003**: Picking a candidate pin MUST resolve to that exact stop, identically to picking from the text list.
- **FR-004**: Every candidate choice MUST offer a `none of these` answer that triggers a guided retry, never a dead end or an invented stop.
- **FR-005**: The passenger MUST be able to decline or dismiss map help at any point during a choice.
- **FR-006**: Declining map help MUST NOT block journey completion; the text list alone MUST suffice.
- **FR-007**: When map display fails, the choice MUST fall back silently to the text list.
- **FR-008**: Repeated `none of these` answers MUST each receive a guided re-prompt, never an unbounded identical loop.
- **FR-009**: Every candidate pin MUST remain reachable and resolvable through the text list with identical outcomes (keyboard and screen-reader parity).

### Key Entities

- **Candidate pin**: A candidate stop shown on the map with a highlighted state while its choice is pending.
- **Fitted viewport**: The map view positioned to include every candidate pin when a choice appears.
- **Decline preference**: The passenger's dismissal of map help, respected for the rest of that exchange.
- **Guided retry**: The follow-up to `none of these`: rephrasing help or a re-listed choice, never a repeated bare prompt.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every multi-candidate prompt fits all candidate pins in view on first display with candidates highlighted.
- **SC-002**: 9 out of 10 trial unfamiliar passengers resolve a side-of-road choice within two picks using the map.
- **SC-003**: 100% of decline trials still complete the journey through the text list alone.
- **SC-004**: Zero dead-ends follow `none of these` in trials; every such answer yields a retry or an honest refusal with a next step.

## Assumptions

- The existing map component is reused; the fitted viewport covers the candidate bounding area with a small margin (exact margin is a planning-time decision).
- Passengers who already know their exact stops may bypass agent search entirely through direct search; the map helper serves the choosing moment for anyone facing a same-name list, regardless of familiarity.
- Declining map help lasts for the current exchange; a new journey question may offer map help again.
- Guided retries stay bounded and text-based; no new data collection beyond existing aggregate signals.
- The product stays read-only with no accounts; map interactions are not tracked per user.
