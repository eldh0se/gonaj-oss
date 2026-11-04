# Data Model: 016-frontend-ux-polish

**Feature**: 016-frontend-ux-polish | **Date**: 2026-11-04

No backend entities. All state is existing frontend React state, re-routed per FR. This document records the ownership map so implementers touch the right prop.

## MarkerLabels (FR-010)

- Source: `MapView` `markers` prop + live map bounds (`getBounds`); derived `labelMode = off | full (1–12 visible) | compact (13–24 visible)`.
- Consumers: every rendered marker layer (`L.marker` endpoints, `circleMarker` intermediates) via `bindTooltip(name, {permanent, themed class + compact flag})` / `unbindTooltip`.
- Transitions: markers change or `moveend` fires → recompute mode → bind/unbind; no fetch involved.
- Validation: crowded views bind zero tooltips; uncrowded views label every marker (compact class only in the 13–24 band); endpoint `title`/`alt` unaffected.

## RouteFocus (FR-004)

- Source: `overlay.detail.stops` (`App.jsx: getRoute` payload: `{id, name, stops: [{stop:{id,name,lat,lon}, is_origin, is_terminus, position}]}`).
- Consumers: `MapView` props `markers` (route stops only while open), `highlight` (route polyline), `fitBounds` (route bounds), plus distinct origin/destination marker rendering.
- Transitions: route open → focus props; close (`navigate("/")`) → `markers=area.markers`, `highlight=null`, `fitBounds=null`.
- Validation: origin/terminus carry accessible labels distinct from intermediate `circleMarker`.

## StopFocus (FR-009)

- Source: `stopCard.detail` (`getStop` payload `{id, name, lat, lon, serving_routes}`).
- Consumers: `MapView` prop `center` (`{lat, lon, nonce}`); `markers` stays `area.markers`.
- Validation: centering never hides area markers.

## RecordingState (FR-005)

- Source: `JourneyPanel` `recording` boolean + pointer timestamps.
- Transitions: `pointerdown` → hold timer/arm; `pointerup/leave` <~300ms → inline hint, no capture; hold → `recording=true` (pulsing dot, live-region message, Ask disabled); release → transcribe → idle.
- Validation: short tap never calls `getUserMedia`/`MediaRecorder`/`postTranscribe`.

## QueryMode (FR-006/FR-007)

- Sources: ask `state` (`idle|loading|ok|disambiguate|refuse|error`), `question`, `cards/paging/filter`; direct `fromText/fromStop/toText/toStop`, `direct` (`idle|loading|ok|empty|error`); candidate highlights via `onShowCandidates`.
- Transitions: ask submit / transcribe-complete → direct reset; direct input/select/Find → ask reset; `state.status==loading` → direct controls disabled + Stop visible; Stop → `askAbort.abort()`, idle, question preserved.
- Validation: `findDirectRoutes` no-ops while ask loading; no concurrent ask+direct fetch.

## AppVersion (FR-008)

- Source: build-time defines `__APP_VERSION__` (default `0.1.0` from `package.json`), `__APP_SHA__` (7-char, empty when unknown), `__APP_BUILT_AT__` (UTC, empty when unknown).
- Render: `v{version}+{sha7} · built {UTC}` when SHA known (time appended when known); `v{version}` (+ `· built {UTC}` when time known) otherwise.
- Validation: UI renders with all defines missing.
