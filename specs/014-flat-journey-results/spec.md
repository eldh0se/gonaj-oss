# Feature Specification: Flat Paginated Journey Results

**Feature Branch**: `014-flat-journey-results`

**Created**: 2026-11-03

**Status**: Draft

**Input**: User description: "Feature: flat paginated journey results. Passenger asks area to area and gets many direct options. What changes: backend stops grouping by operator and returns flat relevance-ranked options with page pagination, frontend renders them as cards with Load more and current-page filter. Why: operator groups hide relevance, unbounded prose overflows, frontend ignores option_groups. Out of scope: server-side operator filter, bbox ends, token-weighted relevance tuning."

## Clarifications

### Session 2026-11-03

- Q: Should the client be allowed to request its own page size, or is the page size fixed by the server? → A: Client may request a page size up to a server-enforced maximum; larger values are clamped.
- Q: Which card fields should the text filter match against? → A: Stop names, service names, and operator labels.
- Q: Should the bounded prose summary have a hard character cap so SC-004 is mechanically testable? → A: Yes, 1000 characters maximum.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Area-to-area options as a flat ranked list with pages (Priority: P1)

A passenger asks for direct service between two areas (e.g. "buses from Kaloor to Fort Kochi") and gets many direct options. Instead of per-operator groups, the journey answer returns one flat list ordered by the existing relevance ranking, delivered one page at a time with the total count so the UI can page through everything.

**Why this priority**: This is the core defect. Operator groups bury the most relevant option inside whichever group its operator happens to head, and the full enumeration has no bound. A flat ranked page puts the best options first and makes the full set reachable.

**Independent Test**: Ask an area-to-area question with many direct options and confirm the answer carries a flat `options` array in relevance order plus pagination info (`page`, total option count); requesting page 2 returns the next slice with no overlap.

**Acceptance Scenarios**:

1. **Given** an area-to-area question with more direct options than one page, **When** the passenger asks, **Then** the answer returns the first page of flat options in relevance order, the total option count, and no operator grouping.
2. **Given** a total count spanning several pages, **When** page 2 is requested, **Then** it returns the next options in the same relevance order with no repeats and no omissions across pages.
3. **Given** a question with fewer options than one page, **When** the passenger asks, **Then** all options arrive in a single page and the response says there is nothing more to load.

---

### User Story 2 - Option cards with pager and a filter (Priority: P1)

The passenger sees the first page of direct options as cards (from stop, to stop, service names, evidence link) with a Prev/Next pager matching the routes/stops tabs and a text filter. Paging fetches that page from the server and replaces the cards; the filter narrows the visible cards on the current page, and changing page clears the filter.

**Why this priority**: Cards plus paging are what make the flat pages usable — without them the paged backend has no user-visible effect, and the filter is how a passenger copes with dozens of options.

**Independent Test**: Render an answer with several pages of options, page forward then back with the pager, type a filter term, and change page — confirm each page renders in relevance order with "Page X of Y · N options", the pager hides on a single page, and changing page clears the filter.

**Acceptance Scenarios**:

1. **Given** a multi-page answer, **When** the passenger activates Next, **Then** the next page of cards replaces the list in relevance order with Prev enabled and the pager position updated.
2. **Given** the current page of option cards, **When** the passenger types a filter term, **Then** only cards on that page matching the term stay visible.
3. **Given** an active filter, **When** the passenger clears it, **Then** all cards on the current page reappear in their original order.

---

### User Story 3 - Compact answer with operator info preserved (Priority: P2)

The prose answer becomes a short summary (how many direct options, naming the top one) instead of enumerating every group, so it never overflows the answer panel. Each option card still shows its operator, so no information is lost by dropping the groups.

**Why this priority**: Bounded prose fixes the overflow defect, and keeping the operator on each card preserves the one thing the groups were good for — knowing who runs each service.

**Independent Test**: Ask an area-to-area question with many options and confirm the prose is a short summary while every card carries its operator label.

**Acceptance Scenarios**:

1. **Given** many direct options, **When** the answer arrives, **Then** the prose summarizes (count plus top option) instead of enumerating every option.
2. **Given** any option card, **When** the passenger reads it, **Then** it names the operator running that service.

---

### Edge Cases

- No direct options: the existing honest refusal is unchanged (no empty pages, no cards, no pager).
- Ambiguous stops: the existing disambiguation flow is unchanged; paging applies only to answered option lists.
- Filter matches nothing: show the plain empty state ("no loaded options match") with the filter intact so the passenger can clear it.
- Page beyond the last page: returns an empty options array with the same totals, never an error.
- Option count exactly fills whole pages: on the last full page Next is disabled (no empty trailing page fetch); the pager hides entirely when there is only one page.
- Route overlay: opening a route evidence link and closing the overlay keeps the journey results — evidence links navigate client-side, so no search state is lost.
- Model-outage fallback answers: unchanged local-fallback shape with no option pages.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The journey answer MUST return direct options as one flat array ordered by the existing relevance ranking, with no per-operator grouping.
- **FR-002**: Option lists MUST be paginated: the request accepts a page number and page size, and the answer carries the current page, the page size, and the total option count.
- **FR-003**: The frontend MUST render options as cards (from stop, to stop, service names with evidence links, operator) with a Prev/Next pager matching the routes/stops tabs that fetches the requested page until exhausted.
- **FR-004**: The frontend MUST provide a text filter that narrows the visible cards to matching options among results loaded so far, preserving hidden options until cleared.
- **FR-005**: The prose answer MUST be a bounded summary (option count plus top option) of at most 1000 characters and MUST NOT enumerate the full option list.
- **FR-006**: Every option MUST carry its operator label and route network string on the card (both display-only); there is no server-side operator filter.
- **FR-007**: Disambiguation, refusal, and model-fallback response shapes MUST stay unchanged; only successful ranked answers gain the flat paged options.

### Key Entities

- **JourneyOption**: One direct service between the resolved stops — from/to stop names, service names with evidence links, operator label, and its relevance rank position.
- **PagedOptions**: The page slice the passenger sees — the flat option array for the requested page plus the current page number, page size, and total option count.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An area-to-area question with 25+ direct options returns the first page in relevance order with the total count, and every option is reachable through paging with no repeats.
- **SC-002**: A passenger can go from the first card to an option past the first page using only the pager, with order preserved.
- **SC-003**: Typing a filter term leaves only matching cards visible, and clearing it restores all cards on the current page in order.
- **SC-004**: The prose answer for a 25+ option question is at most 1000 characters (summary only, no enumeration).

## Assumptions

- Default page size is 5; the client may request up to a server maximum of 20, and larger values are clamped instead of erroring.
- The filter matches against text already loaded in the client: stop names, service names, and operator labels; it does not fetch from the server.
- Relevance order reuses the existing ranking unchanged — no token-weighted tuning (explicitly out of scope).
- `option_groups` is removed from the answer; the bounded prose summary is the compatibility path for old renderers, and the 004/010 answer contracts are updated at plan time.
- Page numbering starts at 1; page size and totals are non-negative integers.
- `destinations` (up to 5 reachable stops) behavior is unchanged by the flattening.
