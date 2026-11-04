import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { tileConfig } from "../api/tiles.js";

const DEFAULT_CENTER = [9.967, 76.28];
const DEFAULT_ZOOM = 13;
const DEBOUNCE_MS = 300;

// Permanent name labels show while the in-bounds stop count stays readable;
// above this count the pins render bare to avoid clutter. Sized with room
// for roughly one zoom-out of density growth past a proven-readable view.
// The dense-but-wanted band renders compact (smaller) instead of full-size.
const FULL_LABEL_MAX = 12;
const MAX_LABELLED_VISIBLE = 24;

function boundsOf(map) {
  const b = map.getBounds();
  return {
    west: b.getWest(),
    south: b.getSouth(),
    east: b.getEast(),
    north: b.getNorth(),
  };
}

function markersInBounds(markers, bounds) {
  return (markers ?? []).filter(
    (m) =>
      typeof m?.lat === "number" &&
      typeof m?.lon === "number" &&
      m.lat >= bounds.south &&
      m.lat <= bounds.north &&
      m.lon >= bounds.west &&
      m.lon <= bounds.east
  );
}

// Leaflet adapter: the only module that touches the map provider.
// Props in: markers, highlight, tile config. Callbacks out: debounced
// area changes, stop selection. Never fetches transit data itself.
export default function MapView({
  markers = [],
  highlight = null,
  center = null,
  selectedId = null,
  highlightIds = [],
  fitBounds = null,
  onAreaChange,
  onSelectStop,
}) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const markerLayerRef = useRef(null);
  const highlightLayerRef = useRef(null);
  const onAreaRef = useRef(onAreaChange);
  onAreaRef.current = onAreaChange;
  const pinsRef = useRef([]);
  const appliedLabelsRef = useRef("off");
  const buildKeyRef = useRef(null);
  const [labelMode, setLabelMode] = useState("off");

  function computeLabelMode(list) {
    const map = mapRef.current;
    if (!map) return "off";
    const visible = markersInBounds(list, boundsOf(map));
    if (visible.length === 0 || visible.length > MAX_LABELLED_VISIBLE) {
      return "off";
    }
    return visible.length <= FULL_LABEL_MAX ? "full" : "compact";
  }

  function applyLabels(mode) {
    for (const { pin, marker } of pinsRef.current) {
      if (mode === "off") {
        pin.unbindTooltip();
      } else {
        pin.bindTooltip(marker.name ?? "Unnamed stop", {
          permanent: true,
          direction: "top",
          offset: [0, -9],
          className:
            mode === "compact"
              ? "gonaj-marker-label is-compact"
              : "gonaj-marker-label",
          opacity: 1,
        });
      }
    }
    appliedLabelsRef.current = mode;
  }

  function refreshLabels() {
    setLabelMode(computeLabelMode(pinsRef.current.map((entry) => entry.marker)));
  }
  const onSelectStopRef = useRef(onSelectStop);
  onSelectStopRef.current = onSelectStop;
  const [tilesFailed, setTilesFailed] = useState(false);

  useEffect(() => {
    const onResize = () => mapRef.current?.invalidateSize();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  useEffect(() => {
    const map = L.map(containerRef.current).setView(DEFAULT_CENTER, DEFAULT_ZOOM);
    mapRef.current = map;
    const tiles = L.tileLayer(tileConfig.url, {
      attribution: tileConfig.attribution,
      maxZoom: 19,
    });
    tiles.on("tileerror", () => setTilesFailed(true));
    tiles.addTo(map);
    markerLayerRef.current = L.layerGroup().addTo(map);
    highlightLayerRef.current = L.layerGroup().addTo(map);

    let timer = null;
    const emit = () => {
      clearTimeout(timer);
      timer = setTimeout(() => onAreaRef.current?.(boundsOf(map)), DEBOUNCE_MS);
    };
    map.on("moveend", emit);
    // Labels follow pan/zoom immediately; area data stays debounced.
    map.on("moveend", refreshLabels);
    emit();

    return () => {
      clearTimeout(timer);
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Declared before the marker build so the mount commit applies labels
  // exactly once: this skips (applied matches), then the build applies fresh.
  useEffect(() => {
    if (appliedLabelsRef.current === labelMode) return;
    applyLabels(labelMode);
  }, [labelMode]);

  useEffect(() => {
    const layer = markerLayerRef.current;
    if (!layer) return;
    // Parent renders hand down fresh array identities; rebuild only when the
    // content actually changed, so a label sync never duplicates layers.
    const key = JSON.stringify([
      markers.map((m) => [m.id, m.lat, m.lon, m.role ?? ""]),
      selectedId ?? null,
      highlightIds ?? [],
    ]);
    if (key === buildKeyRef.current) return;
    buildKeyRef.current = key;
    layer.clearLayers();
    const built = [];
    for (const marker of markers) {
      const selected = marker.id === selectedId;
      const highlighted =
        !selected &&
        Array.isArray(highlightIds) &&
        highlightIds.includes(marker.id);
      let pin;
      // Route endpoints render as labelled pins (keyboard-focusable markers
      // with a name + role), visually distinct from intermediate dots.
      if (marker.role === "origin" || marker.role === "terminus") {
        const kind = marker.role === "origin" ? "Origin" : "Destination";
        const label = `${kind}: ${marker.name ?? "Unnamed stop"}`;
        pin = L.marker([marker.lat, marker.lon], {
          title: label,
          alt: label,
          icon: L.divIcon({
            className: `gonaj-focus-marker is-${marker.role}`,
            iconSize: [16, 16],
          }),
        }).on("click", () => onSelectStopRef.current?.(marker));
      } else {
        pin = L.circleMarker(
          [marker.lat, marker.lon],
          selected
            ? { radius: 10, color: "#ffffff", weight: 3, fillColor: "#084d38", fillOpacity: 1 }
            : highlighted
              ? { radius: 9, color: "#ffffff", weight: 3, fillColor: "#b45309", fillOpacity: 1 }
              : { radius: 7, color: "#ffffff", weight: 2, fillColor: "#0b6e4f", fillOpacity: 0.95 }
        ).on("click", () => onSelectStopRef.current?.(marker));
      }
      pin.addTo(layer);
      built.push({ pin, marker });
    }
    pinsRef.current = built;
    // Single pass: label from the fresh count, then sync state for moveend.
    // React bails out when the value is unchanged, so no extra render loop.
    const mode = computeLabelMode(markers);
    applyLabels(mode);
    setLabelMode(mode);
  }, [markers, selectedId, highlightIds]);

  useEffect(() => {
    const layer = highlightLayerRef.current;
    if (!layer) return;
    layer.clearLayers();
    if (highlight && highlight.length > 0) {
      L.polyline(highlight, { color: "#0b6e4f", weight: 4, opacity: 0.9 }).addTo(layer);
    }
  }, [highlight]);

  const fitKeyRef = useRef(null);
  useEffect(() => {
    if (!mapRef.current) return;
    if (!fitBounds) {
      fitKeyRef.current = null;
      return;
    }
    const key = JSON.stringify(fitBounds);
    if (fitKeyRef.current === key) return;
    fitKeyRef.current = key;
    mapRef.current.fitBounds?.([
      [fitBounds.south, fitBounds.west],
      [fitBounds.north, fitBounds.east],
    ]);
  }, [fitBounds]);

  useEffect(() => {
    if (center && mapRef.current) {
      mapRef.current.setView(
        [center.lat, center.lon],
        Math.max(mapRef.current.getZoom(), 15)
      );
    }
  }, [center]);

  return (
    <div className="gonaj-map">
      <div
        ref={containerRef}
        className="gonaj-map-container"
        data-testid="map-container"
      />
      {tilesFailed && (
        <p role="status" className="gonaj-tiles-notice">
          Map imagery is unavailable right now. Stops, search, and route
          details still work below.
        </p>
      )}
    </div>
  );
}
