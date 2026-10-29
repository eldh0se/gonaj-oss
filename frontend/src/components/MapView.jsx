import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { tileConfig } from "../api/tiles.js";

const DEFAULT_CENTER = [9.967, 76.28];
const DEFAULT_ZOOM = 13;
const DEBOUNCE_MS = 300;

function boundsOf(map) {
  const b = map.getBounds();
  return {
    west: b.getWest(),
    south: b.getSouth(),
    east: b.getEast(),
    north: b.getNorth(),
  };
}

// Leaflet adapter: the only module that touches the map provider.
// Props in: markers, highlight, tile config. Callbacks out: debounced
// area changes, stop selection. Never fetches transit data itself.
export default function MapView({
  markers = [],
  highlight = null,
  center = null,
  onAreaChange,
  onSelectStop,
}) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const markerLayerRef = useRef(null);
  const highlightLayerRef = useRef(null);
  const onAreaRef = useRef(onAreaChange);
  onAreaRef.current = onAreaChange;
  const onSelectStopRef = useRef(onSelectStop);
  onSelectStopRef.current = onSelectStop;
  const [tilesFailed, setTilesFailed] = useState(false);

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
    emit();

    return () => {
      clearTimeout(timer);
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const layer = markerLayerRef.current;
    if (!layer) return;
    layer.clearLayers();
    for (const marker of markers) {
      L.circleMarker([marker.lat, marker.lon], { radius: 7 })
        .on("click", () => onSelectStopRef.current?.(marker))
        .addTo(layer);
    }
  }, [markers]);

  useEffect(() => {
    const layer = highlightLayerRef.current;
    if (!layer) return;
    layer.clearLayers();
    if (highlight && highlight.length > 0) {
      L.polyline(highlight).addTo(layer);
    }
  }, [highlight]);

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
