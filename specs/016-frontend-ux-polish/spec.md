# Feature Specification: Frontend UX Polish

**Feature Branch**: `016-frontend-ux-polish`

**Created**: 2026-11-04

**Status**: Draft

**Input**: User description: "Feature: Frontend journey/search/map UX polish + visible build version. Context: React 18 + Leaflet frontend in `frontend/src/`. Layout in `App.jsx:MapPage` renders `MapView` + `aside.gonaj-results` containing `SearchBox.jsx` above `ResultsList.jsx` tabs `[Journey][Routes][Stops]`. `JourneyPanel.jsx` provides ask-mode question input, press-and-hold Dictate (`onPointerDown/Up/Leave`), direct From/To `StopPicker` + `Find direct routes`. Route detail in `RouteOverlay.jsx` + `.gonaj-overlay` in `App.css`. Mobile breakpoint `max-width:48rem` currently allows `max-height:70dvh`. Version only in `frontend/package.json:0.1.0`, not displayed. (1) Scoped main search: Move debounced `SearchBox` from above tabs into only `Routes` and `Stops` tab panels in `ResultsList.jsx`. `Journey` tab must show no main search. Preserve search, pagination (`Pager`), loading/no-match/error states. Keep sticky behavior working inside tabs. Goal: save vertical space, enlarge results area. (2) Mobile route-detail height: Cap `RouteOverlay` / stop card on mobile to ≤50% viewport height (e.g. `45-50dvh`), keep map visible and interactive. Make detail scrollable internally. [Superseded: no collapse/expand control — expanded-only with close restoring tab content, per Clarifications.] Do not change desktop right-dock `min(400px,100%)` behavior. Update `@media` in `App.css`. (3) Focus map on selected route: When `/routes/:routeId` detail is open from `Journey` or `Routes` results, `MapView` must show only that route polyline + its stops. Hide generic `area.markers`. Mark origin vs destination with distinguishable markers (color/shape + accessible labels, distinct from intermediate `circleMarker`). Fit bounds to route. On close, restore area markers. (4) Press-and-hold transcribe hint + recording indication: In `JourneyPanel.jsx` Dictate button add persistent hint `Press and hold to record`, `title`/tooltip, and short-tap detection: quick click (<~300ms) shows inline hint explaining press-and-hold. While `recording==true` show clear recording state: pulsing/red dot animation, `Listening… release to send` with `role=status`/`aria-live`, disable Ask to avoid overlap. (5) Mutual clear direct vs ask/transcribe: Starting Ask (submit) or successful transcribe must clear direct inputs `fromText/fromStop/toText/toStop`, candidate menus, and `direct` results. Starting direct search (typing/selecting/Find) must clear `question`, ask `state/cards/paging/filter`, and candidate map highlights. Cover mid-selection abandonment both ways. (6) Disable direct during ask + stop option: While `state.status==loading` disable From/To inputs, candidate selection, and `Find direct routes`. Show `Stop` button aborting `askAbort`, restoring idle without clearing question text. Prevent `findDirectRoutes` from running concurrently. (7) Visible frontend version: Display deployed frontend version readable in UI (footer — superseded refinement from header/footer/about, per Clarifications/FR-008 — e.g. `v0.1.0+<sha>`). Source from `package.json` version + Vite build-time `__APP_VERSION__` / git SHA + build time. Add `vitest` coverage for rendering and fallback when unavailable."

## Clarifications

### Session 2026-11-04

- Q: Short-tap feedback for the Dictate button — inline hint or toast? → A: Inline hint text near the button (simpler, testable, no toast system needed).
- Q: Should the mobile route overlay start collapsed or expanded? → A: Expanded with a collapse affordance (current information stays visible; user can collapse). [Superseded — collapse/expand dropped per Q below; overlay is expanded-only with close restoring tab content.]
- Q: Should the capped mobile overlay keep a collapse/expand control, or rely on close alone? → A: Drop it, close only (capped height plus internal scroll already keeps the map visible; close restores the results underneath).
- Q: Exact version string and fallback when build info is missing? → A: `v{version}+{sha7}` when both known; `v{version}` when the SHA is unavailable.
- Q: Where in the UI should the frontend version string live? → A: Footer as `footer.gonaj-version`, small muted text, format `v0.1.0+<sha> · built <UTC time>`.
- Q: Should opening a stop detail card also focus the map, or is focus reserved for route detail only? → A: Both — a stop card centers the map on that stop while area markers stay.

### Update 2026-11-04 (marker name labels)

- Q: Tooltip on hover or permanent label? → A: Permanent name labels once uncrowded.
- Q: Zoom threshold? → A: Gate on visible stop count (readable handful, ≤6 in view) instead of a fixed zoom — labels appear before the map is so zoomed-in that only 3–4 stops show.
- Q: Route focus only or area markers too? → A: Both — any rendered marker (area or route focus) gets a name label when uncrowded.

### Tuning 2026-11-04 (field feedback: threshold too shy)

- ≤6 hid labels at real-world density (gone three zoom-out presses from max on a phone). Raised to ≤24 — room for roughly one zoom-out of density growth past a proven-readable view, so the third-press level labels and the bare city view still stays bare. Single knob: `MAX_LABELLED_VISIBLE`.
- ≤24 full-size labels cluttered the fourth-press level (opposite-side stops converging). Split into two tiers: full-size ≤12, compact ≤24, bare above — the dense-but-wanted level stays distinguishable without the clutter.
- Q: Routes/Stops search query — shared or independent per tab? → A: Shared — both tab boxes share a single query state; switching tabs preserves query text; pagination remains independent per tab.
- Q: When a route opened from Journey disambiguation is closed, restore candidate highlights? → A: Restore — closing MUST restore the prior `candidateView` highlights in addition to area markers.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Scoped main search per tab (Priority: P1)

A passenger browsing the Routes tab types in the search box inside that tab and pages through matching routes; switching to the Stops tab shows the search box inside that tab instead; the Journey tab shows no main search box at all. Search, pager, loading, no-match, and error states behave exactly as before, and the sticky results header keeps working inside each tab.

**Why this priority**: Frees vertical space and enlarges the results area on every screen size; it restructures the primary results layout everything else sits in.

**Independent Test**: Render with journey content present, switch across Journey/Routes/Stops tabs, and confirm the search box appears only inside Routes and Stops panels with working search, pager, and sticky behavior, and never in the Journey panel.

**Acceptance Scenarios**:

1. **Given** the results panel, **When** the passenger views the Journey tab, **Then** no main search box is shown.
2. **Given** the Routes or Stops tab, **When** the passenger types a query, **Then** debounced search, pager, loading, no-match, and error states work as before inside that tab.
3. **Given** scrolled tab content, **When** the passenger scrolls, **Then** the sticky results header keeps working inside the tab.

---

### User Story 2 - Compact mobile route detail (Priority: P1)

A passenger on a phone opens a route from results and still sees the map: the detail sheet covers at most half the viewport and scrolls internally for long stop lists. Closing it restores the previously visible tab content. Desktop docking is untouched.

**Why this priority**: On small screens the current sheet hides the map it is supposed to annotate; capping it restores the map-first experience.

**Independent Test**: Render the route overlay at a mobile viewport, assert its height never exceeds 50% of the viewport, scroll a long stop list inside it, close it and confirm the previously visible tab content returns, and confirm desktop width still docks at `min(400px,100%)`.

**Acceptance Scenarios**:

1. **Given** a mobile viewport, **When** route detail opens, **Then** it occupies at most 50% of viewport height while the map stays visible and interactive.
2. **Given** a long stop list, **When** the passenger scrolls, **Then** only the detail content scrolls internally.
3. **Given** the open detail sheet, **When** the passenger closes it, **Then** the previously visible tab content (search results for Journey, Routes, or Stops) is restored with no search state lost.

---

### User Story 3 - Map focuses on the selected route (Priority: P1)

A passenger opens a route from Journey answers or the Routes tab and the map switches to that route alone: one polyline, only its stops, origin and destination marked distinctly from intermediate stops with accessible labels, bounds fitted to the route. Closing the detail restores the generic area markers.

**Why this priority**: Showing every area marker under a selected route buries the answer the passenger just asked for; focus makes the selection legible.

**Independent Test**: Open a route overlay from Journey results and from the Routes tab, assert only the route polyline and its stops render with distinct origin/destination markers and fitted bounds, then close and assert area markers return.

**Acceptance Scenarios**:

1. **Given** an open route detail from Journey or Routes results, **When** the map renders, **Then** only that route's polyline and stops are shown (generic area markers hidden) with bounds fitted to the route.
2. **Given** the focused route, **When** the passenger inspects its stops, **Then** origin and destination markers are distinguishable by color/shape and carry accessible labels distinct from intermediate circle markers.
3. **Given** the overlay is closed, **When** the map renders again, **Then** the generic area markers are restored.
4. **Given** an open stop detail card, **When** the map renders, **Then** it centers on that stop with area markers still visible.
5. **Given** 12 or fewer stops visible in the current map bounds (area or route focus alike), **When** the map renders, **Then** each visible marker carries a full-size permanent name label; with 13–24 visible the labels render compact; with more stops in view, pins stay bare.

---

### User Story 4 - Discoverable press-and-hold dictation (Priority: P2)

A passenger finds the Dictate button with its `Press and hold to record` hint, taps it quickly and learns press-and-hold is required, then holds it and sees an unmistakable recording state (`Listening… release to send`, pulsing red dot) while Ask stays disabled until release.

**Why this priority**: Press-and-hold is undiscoverable without a hint, and recording without feedback looks broken; both cause failed voice attempts.

**Independent Test**: Render the Dictate button, assert the persistent hint and tooltip, quick-click to assert the inline press-and-hold explanation, start a hold to assert the recording state (pulsing dot, live-region message, Ask disabled), and release.

**Acceptance Scenarios**:

1. **Given** the Dictate button, **When** it renders, **Then** the `Press and hold to record` hint and tooltip are always visible.
2. **Given** a quick click under ~300ms, **When** it is released, **Then** an inline hint explains press-and-hold instead of starting a recording.
3. **Given** an active recording, **When** it is in progress, **Then** the pulsing red dot and `Listening… release to send` live-region message show while Ask is disabled.

---

### User Story 5 - Direct and ask modes clear each other (Priority: P2)

A passenger who typed a journey question and then starts picking From/To stops sees the question, answer cards, pager, filter, and map highlights reset; conversely, submitting an ask (or completing a dictation) wipes the From/To inputs, candidate menus, and direct results. Abandoning either mode mid-selection leaves no stale state behind.

**Why this priority**: Mixing two query modes on screen at once shows answers to a question the passenger is no longer asking — the most confusing state in the panel.

**Independent Test**: Type a question, start direct input, and assert ask state is cleared; then set direct inputs and results, submit an ask (and separately complete a transcribe), and assert direct state is cleared — including mid-selection abandonment both ways.

**Acceptance Scenarios**:

1. **Given** ask state (question, cards, filter, highlights), **When** the passenger types/selects/Finds in direct mode, **Then** all ask state is cleared.
2. **Given** direct state (inputs, candidates, results), **When** the passenger submits an ask or completes a transcribe, **Then** all direct state is cleared.
3. **Given** a half-made direct selection, **When** the passenger submits an ask, **Then** no partial direct state survives (and vice versa).

---

### User Story 6 - Ask in progress locks direct mode (Priority: P2)

A passenger submits a question and, while the answer loads, finds From/To inputs, candidate selection, and Find disabled — plus a Stop button that aborts the request, restores idle, and keeps the question text. Direct search can never run concurrently with an ask.

**Why this priority**: Concurrent ask + direct races two model/dataset flows and their map highlights; locking plus an abort path keeps one query in flight at a time.

**Independent Test**: Submit an ask, assert direct controls disabled and Stop visible during loading, abort and assert idle with question text preserved and no direct search fired, and separately let an ask finish to assert controls re-enable.

**Acceptance Scenarios**:

1. **Given** an ask in loading state, **When** the panel renders, **Then** From/To inputs, candidate selection, and Find are disabled and a Stop button is shown.
2. **Given** the Stop button, **When** activated, **Then** the ask aborts, the panel returns to idle, and the question text is preserved.
3. **Given** a loading ask, **When** direct controls are exercised, **Then** no direct search runs.

---

### User Story 7 - Visible frontend version (Priority: P3)

A passenger (or tester verifying a deploy) reads the running frontend version in the UI, e.g. `v0.1.0+<sha>`; when build metadata is missing the plain package version still shows.

**Why this priority**: Deploy verification currently requires opening devtools; a visible version makes "which build is live?" answerable by anyone.

**Independent Test**: Render the app with build metadata present and assert the full `v{version}+{sha7}` string shows; render without it and assert the plain-version fallback shows.

**Acceptance Scenarios**:

1. **Given** build metadata, **When** the app renders, **Then** the footer shows `v{version}+{sha7} · built <UTC time>` as small muted text.
2. **Given** missing build metadata, **When** the app renders, **Then** the plain `v{version}` fallback shows in the footer instead of nothing.

---

### Edge Cases

- Sticky tab headers must keep working after the search box moves inside tab panels (no sticky context broken by the move).
- Desktop route dock (`min(400px,100%)`) is byte-for-byte unchanged; only the `max-width:48rem` block changes.
- Closing the route/stop overlay restores the previously visible tab content (search results for Journey, Routes, and Stops alike) — no search state is lost; closing a route opened from Journey disambiguation additionally restores prior candidate map highlights.
- No collapse/expand control exists; the sheet is expanded-only up to the height cap and close restores the tabs.
- Permanent name labels appear only when the visible stop count is small (≤24 in bounds, full-size ≤12); panning/zooming across the thresholds toggles them without refetching.
- The pulsing recording dot honors `prefers-reduced-motion` (static red dot, no animation).
- The `Listening…` message uses `role=status`/`aria-live` so screen readers announce recording start; Ask stays disabled until recording ends.
- Short-tap threshold (~300ms) only triggers the inline explanation; it never starts audio capture.
- Aborting an ask never clears the question text; mutual clear never wipes the mode the passenger just activated.
- Version string never blocks rendering: if all build metadata is missing, the UI still renders with the plain fallback.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The main `SearchBox` MUST render inside the Routes and Stops tab panels only (never in the Journey tab), preserving debounced search, `Pager` pagination, and loading/no-match/error states in each tab. Both tab boxes share a single query state (switching tabs preserves query text); pagination remains independent per tab.
- **FR-002**: Sticky results-header behavior MUST keep working inside tab panels after the search move.
- **FR-003**: On viewports at or below `48rem`, the route/stop detail overlay MUST occupy at most 50% of viewport height, scroll its content internally, keep the underlying map visible and interactive, and offer close restoring the previously visible tab content; it MUST NOT include a collapse/expand control; desktop docking MUST stay `min(400px,100%)`.
- **FR-004**: While a route detail from Journey or Routes results is open, `MapView` MUST render only that route's polyline and stops (generic area markers hidden), fit bounds to the route, mark origin/destination distinctly from intermediate stops (color/shape plus accessible labels), and restore area markers on close. When the route was opened from Journey disambiguation, closing MUST additionally restore the prior candidate highlights (`candidateView`).
- **FR-005**: The Dictate button MUST show a persistent `Press and hold to record` hint plus tooltip; a sub-~300ms tap MUST show an inline press-and-hold explanation without starting capture; while recording, a pulsing red dot plus `Listening… release to send` (`role=status`/`aria-live`) MUST show and Ask MUST be disabled.
- **FR-006**: Submitting an ask or completing a transcribe MUST clear direct inputs, candidate menus, and direct results; starting direct input (typing/selecting/Find) MUST clear the question, ask state (cards/paging/filter), and candidate map highlights — including mid-selection abandonment both ways.
- **FR-007**: While ask status is loading, From/To inputs, candidate selection, and Find MUST be disabled with no concurrent direct search; a Stop button MUST abort `askAbort`, restore idle, and preserve question text.
- **FR-008**: The footer MUST display the deployed frontend version as small muted text (`footer.gonaj-version`): `v{version}+{sha7} · built <UTC time>` when build metadata exists, `v{version}` (plus `· built <UTC time>` when the time is known) otherwise, sourced from `package.json` plus build-time version/SHA/time values.
- **FR-009**: When a stop detail card is open, `MapView` MUST center on that stop while keeping generic area markers visible (unlike route focus, which hides them).
- **FR-010**: Name labels are two-tiered by visible stop count (area markers and route-focus stops alike): 12 or fewer in bounds → full-size permanent labels; 13–24 → compact permanent labels (same names, smaller); above 24 all labels MUST be hidden to avoid clutter. Endpoint pins keep their accessible titles regardless of label state.

### Key Entities

- **RouteFocus**: the selected route's polyline plus its stop list with origin/destination roles — drives map focus, distinct markers, and bounds fitting.
- **RecordingState**: dictate hold state (`recording`, live-region message, Ask disabled) — drives the recording indicator and tap-vs-hold behavior.
- **QueryMode**: which input mode owns the panel (ask vs direct) — drives mutual clearing and the loading lock.

### Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The Journey tab shows no main search box while Routes and Stops tabs share a single query, page independently, and keep sticky headers intact.
- **SC-002**: At a 390px-wide viewport, opening route detail never covers more than half the viewport; the map stays interactive and closing restores the previously visible tab content.
- **SC-003**: With a route open, the map shows exactly that route's polyline and stops with labeled origin/destination markers; closing restores area markers and prior Journey candidate highlights. With a stop card open, the map centers on that stop while area markers stay visible. Zoomed-in views (≤12 stops in bounds) show full-size permanent name labels on every marker, compact ones up to 24.
- **SC-004**: A quick tap on Dictate explains press-and-hold without recording; a hold shows the pulsing dot, live-region message, and disabled Ask until release.
- **SC-005**: Starting either mode provably clears the other's state (inputs, results, filters, highlights) in both directions, including mid-selection.
- **SC-006**: During ask loading, direct controls are disabled, Stop aborts to idle with question text intact, and no direct search fires.
- **SC-007**: The running build's version string is readable in the UI, with the plain-version fallback rendering when build metadata is absent.

## Assumptions

- Short-tap feedback is an inline hint near the button (not a toast system), per clarify.
- The mobile sheet is expanded-only up to the height cap with no collapse/expand control; close restores the tabs, per clarify.
- Version lives in the footer (`footer.gonaj-version`, small muted text) as `v{version}+{sha7} · built <UTC time>`; SHA part omitted when unavailable, per clarify.
- The pulsing dot animation is disabled under `prefers-reduced-motion` (static red dot instead).
- `Press and hold to record` wording, `Listening… release to send`, and the ~300ms tap threshold are taken verbatim from the request as the shipped strings.
- Existing search debounce timing, pager behavior, and error message wording are unchanged — only the search box's placement moves; Routes/Stops share one query state with independent pagination.
- Mobile detail reuses the existing overlay with capped height — no new bottom-sheet component.
- No backend changes: version values come from build-time injection; no new API.
- Label thresholds (full-size ≤12, compact ≤24, tuned from ≤6 after phone field feedback) are tunable constants (`FULL_LABEL_MAX`, `MAX_LABELLED_VISIBLE` in `MapView.jsx`); label styling reuses existing theme tokens via `.gonaj-marker-label` (+`.is-compact`).
