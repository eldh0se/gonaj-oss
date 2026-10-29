# Feature Specification: Route Map

**Feature Branch**: `005-route-map`

**Created**: 2026-10-29

**Status**: Draft

**Input**: User description: "design 005 as one page with two views (map-browse + route detail overlay), with the chat panel specified to dock into that same page. That keeps the page count at one, satisfies all existing references, and leaves room to split into real routes later if the UI grows."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse stops and routes on the map (Priority: P1)

A passenger opens the map and sees their area's stops and
routes. They pan and zoom to explore, tap a stop to see which
routes serve it, and tap a route to see its full path and stops.
When the viewed area is too large to list, the map says so and
asks them to zoom in rather than showing a misleadingly sparse
map.

**Why this priority**: Seeing what exists nearby is the first
half of the MVP validation question ("How do I get from A to
B?"). Without a browsable map, neither route discovery nor the
future journey helper has a visual surface to point at.

**Independent Test**: Load the map over an area with known stops
and routes, and confirm the expected stops render as markers and
the expected routes render; pan to an empty area and confirm the
empty state; zoom out to a state-sized area and confirm the
zoom-in guidance with no partial rendering.

**Acceptance Scenarios**:

1. **Given** the map loaded over an area containing stops,
   **When** the passenger looks at the map, **Then** each stop
   in the area renders as a marker and each served route is
   reachable from the stop.
2. **Given** the passenger pans or zooms the map, **When** the
   new area loads, **Then** the markers refresh to exactly the
   stops inside the new area (stops on the boundary are
   included).
3. **Given** a map area too large to list, **When** it loads,
   **Then** no stops render and the map shows guidance asking
   the passenger to zoom in — a partial marker set is never
   shown.
4. **Given** a map area with no stops, **When** it loads,
   **Then** the map shows an explicit empty state, not an
   error and not a silently blank map.
5. **Given** a stop marker, **When** the passenger selects it,
   **Then** the map shows the stop's name and the routes that
   serve it, each leading to the route detail view.
6. **Given** the read API is unreachable, **When** the map
   loads, **Then** the passenger sees a plain-language message
   explaining the map cannot load right now, not a broken map
   or a technical dump.

---

### User Story 2 - Search routes and stops by text (Priority: P1)

A passenger who knows a name — a route, a place, or a stop —
types it and gets matching routes and stops, whether or not
they know where to pan the map. Leaving the search blank browses
everything available.

**Why this priority**: Search is the other half of discovery for
passengers who know names but not geography, and it exercises
the read API's search contract end to end from the UI.

**Independent Test**: Type a known route-name fragment and a
known stop-name fragment, and confirm only matching routes and
stops are offered; clear the search and confirm the full browse
list returns.

**Acceptance Scenarios**:

1. **Given** the search box, **When** the passenger types a
   route-name fragment, **Then** only matching routes are
   offered, each leading to the route detail view.
2. **Given** the search box, **When** the passenger types a
   stop-name fragment, **Then** only matching stops are
   offered, each of which centres the map on that stop when
   picked.
3. **Given** a blank or cleared search, **When** it runs,
   **Then** the full browse list of routes and stops is
   offered (paginated, never an unbounded dump).
4. **Given** a search matching nothing, **When** it runs,
   **Then** the UI says plainly that nothing matched and
   suggests checking the spelling or browsing the map.
5. **Given** any search, **When** it runs, **Then** it queries
   the application's own stop/route data only — no external
   place-search service is ever called.

---

### User Story 3 - Inspect a route in the detail overlay (Priority: P2)

A passenger who has found a candidate route opens it to see its
stops in travelling order, where it starts, and where it ends —
including from a shared evidence link. The detail opens as an
overlay on the same page, and its address can be shared and
reopened directly.

**Why this priority**: This is the destination every evidence
link in the future journey helper points to (`/routes/:id`).
Without it, the chat's citations land nowhere. An overlay on
the one page keeps the page count at one while the address
stays deep-linkable for later.

**Independent Test**: Open a route from search and confirm its
stops appear in travelling order with origin and terminus
marked; copy the address, reload it directly, and confirm the
same overlay opens.

**Acceptance Scenarios**:

1. **Given** a known route, **When** the passenger opens its
   detail, **Then** the overlay shows the route's name, origin,
   destination, operator, and its stops in travelling order
   with the first and last positions marked as origin and
   terminus.
2. **Given** the overlay open, **When** the passenger looks at
   the map behind it, **Then** the route's path and stops are
   highlighted on the map.
3. **Given** the overlay open, **When** the passenger copies
   the address (`/routes/:id`) and opens it directly in a new
   view, **Then** the same map page loads with the same route
   overlay already open.
4. **Given** a route with no recorded stops, **When** the
   passenger opens its detail, **Then** the overlay succeeds
   and states plainly that no stops are recorded — not an
   error and not a blank panel.
5. **Given** a route identifier that does not exist, **When**
   it is opened, **Then** the overlay reports in plain,
   non-technical language that the route could not be found.

---

### User Story 4 - See where the journey chat will live (Priority: P2)

A passenger notices the journey-helper entry point docked into
the same page. It is clearly marked as coming soon and does
nothing yet — it takes no input, makes no calls, and collects
nothing — so the layout is ready for the 004 panel without
shipping a dead control that pretends to work.

**Why this priority**: The 004 chat panel needs a specified
home; reserving the dock now keeps 004's implementation to
filling the slot rather than redesigning the page, while
honesty about its state avoids shipping a control that misleads.

**Independent Test**: Open the map page and confirm the chat
dock region is present, labelled as coming soon, and inert:
activating it sends no request and stores nothing.

**Acceptance Scenarios**:

1. **Given** the map page, **When** it loads, **Then** a chat
   dock region is present in the layout, visibly labelled as
   the future journey helper and marked coming soon.
2. **Given** the dock's entry control, **When** the passenger
   activates it, **Then** nothing is sent anywhere, no input
   is collected, and the control plainly states the helper is
   not available yet.
3. **Given** the dock region, **When** a reviewer inspects
   network traffic while activating it, **Then** zero requests
   are made and zero data is stored.

---

### Edge Cases

- What happens when the passenger shares a `/routes/:id`
  address for a route that no longer exists? The page loads
  the map normally and the overlay reports the plain-language
  not-found state.
- What happens when the passenger pans rapidly across areas?
  In-flight area requests for stale extents are discarded;
  only the latest area renders, so markers never show a mix
  of two areas.
- What happens when the tile service is unreachable? The
  markers, lists, and detail overlay still work over a plain
  background with a notice that map imagery is unavailable —
  transit data never depends on tile imagery.
- What happens when the read API returns an oversized-area or
  empty-area status? The map shows the zoom-in guidance or the
  empty state respectively, exactly as specified, with no
  partial markers.
- What happens on a small screen? The map, overlay, search,
  and dock reflow to a single column; no control is
  unreachable and no content requires horizontal scrolling.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The application MUST be one page: a map-browse
  view and a route-detail overlay on the same page. There MUST
  be no other pages in this feature.
- **FR-002**: `/routes/:id` MUST load the map page with the
  route detail overlay already open for that route, so
  evidence links shared from the future journey helper
  resolve. Any other path MUST show the map-browse view, not
  an error page.
- **FR-003**: The map MUST render stops as markers and served
  routes as reachable from each stop, using the application's
  own read API only. Marker sets MUST always reflect exactly
  one map area; stale extents MUST never mix.
- **FR-004**: Panning or zooming MUST re-query stops for the
  new area with closed bounds (edge stops included). An
  oversized area MUST render zero markers plus zoom-in
  guidance, never a partial set; an empty area MUST render the
  explicit empty state.
- **FR-005**: Text search MUST offer matching routes (by name,
  origin, destination, or served stop name) and matching
  stops (by name), served from the application's own data
  only. Blank search MUST browse all; matching nothing MUST
  say so plainly with a spelling-or-browse hint. The rail
  MUST show result counts with page navigation for routes
  and stops independently.
- **FR-006**: The route detail overlay MUST show the route's
  name, origin, destination, operator, and network; its stops
  in travelling order with origin and terminus marked; and
  the route highlighted on the map behind it.
- **FR-007**: A route with no recorded stops MUST still open
  successfully with an explicit no-stops-recorded statement.
  An unknown route identifier MUST report a plain-language
  not-found state, with no technical details exposed.
- **FR-008**: The layout MUST include the journey-chat dock
  region on the same page, visibly labelled as the future
  journey helper and marked coming soon. The dock's control
  MUST be inert: activating it sends no request, collects no
  input, and stores nothing.
- **FR-009**: Map imagery MUST come from the public tile
  service only, with required attribution, appropriate
  self-identification, no bulk or prefetch downloading, and a
  configurable tile-provider setting. Tile imagery failing
  MUST NOT break markers, lists, or the detail overlay.
- **FR-010**: The map provider integration MUST stay isolated
  so the implementation can change (MapLibre is the recorded
  alternative); search MUST NOT use the public Nominatim
  service or any external place search under any
  circumstance.
- **FR-011**: The UI MUST work without login, user accounts,
  or tracking of any kind, and MUST remain fully usable as a
  single-column layout on small screens with no unreachable
  controls.
- **FR-012**: Read API or tile failures MUST surface as
  plain-language, non-technical messages in place (map, list,
  or overlay), never as broken chrome or technical dumps.
- **FR-013**: The UI MUST use one restrained visual identity:
  white `#ffffff` surfaces, ink `#17201c` text, deep transit
  green `#0b6e4f` as the single signal color (active route,
  selected marker, primary actions), sage `#e7efe9` fills,
  amber `#b45309` reserved for warnings (amber wash `#fdf3e7`
  for warning fills), page backdrop `#f2f5f3`, 1px `#d8dee0`
  borders, 10px radius, and the system font stack with 13px
  list text, 14px route/stop item text for daylight
  readability, and 17px semibold headings. No other hues,
  webfonts, gradients, or shadows beyond a panel shadow.
- **FR-014**: The layout MUST be an app shell that fits
  the viewport with no page scroll: brand header on top,
  map plus results rail in the middle (the rail scrolls
  internally with a sticky search box pinned above its
  tabs, the map fills its area), and the chat dock as
  a slim always-visible footer bar marked with a "Coming
  soon" tag, with the title and padding scaling
  proportionally within fixed bounds. The rail MUST present
  routes and stops as user-selectable tabs, opening directly
  on whichever side holds results. Route and stop details MUST share one right-side
  detail panel over the rail on wide screens and one bottom
  sheet on small screens, with route detail taking
  precedence when both apply.
- **FR-015**: Map symbology MUST mark in-area stops as green
  `#0b6e4f` dots with a white ring, the selected stop with a
  distinct ring, and the open route as a 4px green polyline.
  The overlay MUST show stops as a timeline (dots joined by a
  connecting line confined to their own gutter column that
  never overlaps the stop names, origin and terminus as
  filled dots with pinned labels), not as a numbered list.

### Key Entities *(include if feature involves data)*

- **Map View**: The one page. Carries the current area, the
  marker set for exactly that area, the search state, the open
  overlay (if any), and the chat dock region. Carries no user
  identity and persists nothing.
- **Stop Marker**: One stop rendered on the map. Carries the
  stop's identity, name, and coordinates, and links to its
  serving routes. Edge stops are included in their area.
- **Route Detail Overlay**: One route's full presentation on
  the same page. Carries the route's fields, its ordered
  stops with origin/terminus, its map highlight, and its
  deep-linkable `/routes/:id` address.
- **Search**: One text query over the application's own
  routes and stops. Carries the query text and the matching
  candidates; blank means browse-all; no match is an explicit
  message, not an error.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Over a known dataset, 100% of in-area stops
  render exactly once as markers after every pan/zoom, with
  0 stale-area markers persisting and 0 partial renders for
  oversized areas (zoom-in guidance shown instead).
- **SC-002**: For a known set of name fragments, 100% of
  searches offer only matching routes and stops, blank
  search browses all, and 0 searches call any external
  place-search service (verified by traffic inspection).
- **SC-003**: 100% of route detail opens show stops in
  travelling order with marked origin and terminus, 100% of
  `/routes/:id` addresses opened directly land on the map
  page with the correct overlay, and 100% of unknown ids
  show the plain-language not-found state.
- **SC-004**: The chat dock is present and labelled coming
  soon on 100% of page loads, and activating it produces 0
  requests and 0 stored bytes in 100% of checks.
- **SC-005**: With tile imagery blocked, 100% of marker,
  list, search, and detail flows still complete over a plain
  background with the imagery notice shown.
- **SC-006**: Review confirms 100% of the UI works with no
  accounts and no tracking, all map imagery is the public
  tile service with attribution, and the single-column small
  screen layout has 0 unreachable controls.
- **SC-007**: Review confirms 100% of views use only the
  FR-013 palette, radius, and type scale; the overlay opens
  as a side panel on wide screens and a full-width card on
  small screens; and the open route is visibly distinct on
  the map in 100% of checks.

## Assumptions

- The read API from `specs/003-read-map-api` (routes, stops,
  connectivity, shared envelope, servable dataset, `zoom_in`
  and `empty` statuses) is the only data source; this feature
  adds no backend endpoints and performs no import.
- The `/routes/:id` address convention matches the evidence
  links the 004 journey helper will emit; this feature builds
  the destination those links need, and the 004 panel later
  fills the dock specified here (FR-008).
- One page with an overlay is the whole information
  architecture for this feature; splitting the overlay into a
  separate route page later is explicitly allowed but out of
  scope now.
- The chat dock is intentionally inert in this feature: it
  reserves layout and communicates the roadmap, and the
  interactive helper arrives with 004 — no model, voice, or
  AI behaviour is specified or built here.
- Tile-provider choice (default public tiles) and the
  oversized-area threshold are inherited from the read API
  and constitution; this spec fixes UI behaviour, not those
  values.

