import { act, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import MapView from "./MapView.jsx";

vi.mock("leaflet", async () => {
  const { createLeafletMock } = await import("../test/setup.js");
  const mock = createLeafletMock();
  globalThis.__leafletMock = mock;
  return mock.L;
});

function leafletMock() {
  return globalThis.__leafletMock;
}

function lastMap() {
  const { maps } = leafletMock();
  return maps[maps.length - 1];
}

const MARKERS = [
  { id: 1, name: "Stop A", lat: 9.97, lon: 76.28 },
  { id: 2, name: "Stop B", lat: 9.98, lon: 76.29 },
];

describe("MapView", () => {
  beforeEach(() => {
    const mock = leafletMock();
    mock.maps.length = 0;
    mock.layers.length = 0;
    vi.clearAllMocks();
    vi.useRealTimers();
  });

  it("creates one map with OSM tiles and attribution", () => {
    const noop = () => {};
    render(<MapView markers={[]} onAreaChange={noop} />);
    const mock = leafletMock();
    expect(mock.L.map).toHaveBeenCalledTimes(1);
    expect(mock.L.tileLayer).toHaveBeenCalledTimes(1);
    const [url, opts] = mock.L.tileLayer.mock.calls[0];
    expect(url).toContain("tile.openstreetmap.org");
    expect(opts.attribution).toContain("OpenStreetMap");
  });

  it("renders one marker per stop and reports taps", () => {
    const onSelectStop = vi.fn();
    const noop = () => {};
    render(
      <MapView markers={MARKERS} onAreaChange={noop} onSelectStop={onSelectStop} />
    );
    const mock = leafletMock();
    expect(mock.L.circleMarker).toHaveBeenCalledTimes(2);
    expect(mock.L.circleMarker.mock.calls[0][0]).toEqual([9.97, 76.28]);
    expect(mock.L.circleMarker.mock.calls[0][1]).toMatchObject({
      fillColor: "#0b6e4f",
      color: "#ffffff",
    });
    const firstMarker = mock.L.circleMarker.mock.results[0].value;
    const click = firstMarker.on.mock.calls.find(([event]) => event === "click")[1];
    click();
    expect(onSelectStop).toHaveBeenCalledWith(MARKERS[0]);
  });

  it("replaces markers wholesale when the area changes", () => {
    const noop = () => {};
    const { rerender } = render(<MapView markers={MARKERS} onAreaChange={noop} />);
    rerender(<MapView markers={[MARKERS[0]]} onAreaChange={noop} />);
    const mock = leafletMock();
    const markerLayers = mock.L.layerGroup.mock.results.map((r) => r.value);
    const markerLayer = markerLayers[0];
    expect(markerLayer.clearLayers).toHaveBeenCalled();
    expect(mock.L.circleMarker).toHaveBeenCalledTimes(3);
  });

  it("debounces area changes and emits the latest bounds only", () => {
    vi.useFakeTimers();
    const onAreaChange = vi.fn();
    render(<MapView markers={[]} onAreaChange={onAreaChange} />);
    const map = lastMap();
    expect(onAreaChange).not.toHaveBeenCalled();
    act(() => {
      leafletMock().fire(map, "moveend");
      leafletMock().fire(map, "moveend");
      leafletMock().fire(map, "moveend");
    });
    act(() => {
      vi.advanceTimersByTime(300);
    });
    expect(onAreaChange).toHaveBeenCalledTimes(1);
    expect(onAreaChange).toHaveBeenCalledWith({
      west: 76.2,
      south: 9.9,
      east: 76.35,
      north: 10.0,
    });
  });

  it("rings the selected stop distinctly", () => {
    const noop = () => {};
    render(<MapView markers={MARKERS} onAreaChange={noop} selectedId={2} />);
    const mock = leafletMock();
    expect(mock.L.circleMarker.mock.calls[0][1]).toMatchObject({ radius: 7 });
    expect(mock.L.circleMarker.mock.calls[1][1]).toMatchObject({
      radius: 10,
      fillColor: "#084d38",
    });
  });

  it("centres the map when a stop is picked", () => {
    const noop = () => {};
    const { rerender } = render(<MapView markers={[]} onAreaChange={noop} />);
    rerender(
      <MapView markers={[]} onAreaChange={noop} center={{ lat: 9.5, lon: 76.1 }} />
    );
    expect(lastMap().setView).toHaveBeenCalledWith([9.5, 76.1], 15);
  });

  it("draws the route highlight and clears it when closed", () => {
    const noop = () => {};
    const line = [
      [9.97, 76.28],
      [9.98, 76.29],
    ];
    const { rerender } = render(
      <MapView markers={[]} onAreaChange={noop} highlight={line} />
    );
    const mock = leafletMock();
    expect(mock.L.polyline.mock.calls[0][0]).toEqual(line);
    expect(mock.L.polyline.mock.calls[0][1]).toMatchObject({
      color: "#0b6e4f",
      weight: 4,
    });
    const highlightLayer = mock.L.layerGroup.mock.results.map((r) => r.value)[1];
    rerender(<MapView markers={[]} onAreaChange={noop} highlight={null} />);
    expect(highlightLayer.clearLayers).toHaveBeenCalledTimes(2);
  });

  it("shows an imagery notice when tiles fail, keeping the map mounted", () => {
    const noop = () => {};
    render(<MapView markers={MARKERS} onAreaChange={noop} />);
    const mock = leafletMock();
    const tileLayer = mock.L.tileLayer.mock.results[0].value;
    const onTileError = tileLayer.on.mock.calls.find(
      ([event]) => event === "tileerror"
    )[1];
    act(() => {
      onTileError();
    });
    expect(screen.getByRole("status").textContent).toMatch(/imagery is unavailable/);
    expect(screen.getByTestId("map-container")).toBeTruthy();
  });

  it("refreshes the map size on window resize", () => {
    const noop = () => {};
    render(<MapView markers={[]} onAreaChange={noop} />);
    window.dispatchEvent(new Event("resize"));
    expect(lastMap().invalidateSize).toHaveBeenCalled();
  });

  it("removes the map on unmount", () => {
    const noop = () => {};
    const { unmount } = render(<MapView markers={[]} onAreaChange={noop} />);
    unmount();
    expect(lastMap().remove).toHaveBeenCalled();
  });
});
