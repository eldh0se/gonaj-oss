import { vi } from "vitest";

// jsdom has no matchMedia; map code may probe it.
if (typeof window !== "undefined" && typeof window.matchMedia !== "function") {
  window.matchMedia = () => ({
    matches: false,
    addListener() {},
    removeListener() {},
  });
}

// Build-time version defines (`__APP_*__` via vite.config.js `define`).
// Vitest runs without Vite defines, so default them here; suites covering
// the footer version override per case via `globalThis.__APP_VERSION__`
// (assign for the metadata case, `delete` for the fallback case).
for (const key of ["__APP_VERSION__", "__APP_SHA__", "__APP_BUILT_AT__"]) {
  if (!(key in globalThis)) globalThis[key] = undefined;
}

// Shared Leaflet mock factory for component tests. Tests replace the
// `leaflet` module with the returned `L` object:
//
//   vi.mock("leaflet", () => createLeafletMock().L);
//
// (returning the whole factory object keeps one mock definition per file;
// grab `maps`/`layers` from a hoisted instance when assertions need them.)
export function createLeafletMock() {
  const maps = [];
  const layers = [];

  function makeLayer() {
    const handlers = {};
    const layer = {
      __handlers: handlers,
      on: vi.fn(function on(event, fn) {
        (handlers[event] ??= []).push(fn);
        return this;
      }),
      addTo: vi.fn(function addTo() {
        return this;
      }),
      remove: vi.fn(),
      setStyle: vi.fn(),
      clearLayers: vi.fn(),
      addLayer: vi.fn(),
      bindTooltip: vi.fn(function bindTooltip() {
        return this;
      }),
      unbindTooltip: vi.fn(function unbindTooltip() {
        return this;
      }),
    };
    layers.push(layer);
    return layer;
  }

  const L = {
    __esModule: true,
    default: undefined, // assigned below for `import L from "leaflet"`
    map: vi.fn((container) => {
      const handlers = {};
      const map = {
        __container: container,
        __handlers: handlers,
        setView: vi.fn(function setView() {
          return this;
        }),
        on: vi.fn(function on(event, fn) {
          (handlers[event] ??= []).push(fn);
          return this;
        }),
        off: vi.fn(),
        remove: vi.fn(),
        invalidateSize: vi.fn(),
        getZoom: vi.fn(() => 14),
        fitBounds: vi.fn(function fitBounds() {
          return this;
        }),
        getBounds: vi.fn(() => ({
          getWest: () => 76.2,
          getSouth: () => 9.9,
          getEast: () => 76.35,
          getNorth: () => 10.0,
        })),
      };
      maps.push(map);
      return map;
    }),
    tileLayer: vi.fn(() => makeLayer()),
    circleMarker: vi.fn(() => makeLayer()),
    marker: vi.fn(() => makeLayer()),
    divIcon: vi.fn(() => ({})),
    polyline: vi.fn(() => makeLayer()),
    layerGroup: vi.fn(() => makeLayer()),
  };
  L.default = L;

  function fire(target, event, arg) {
    for (const fn of target.__handlers[event] ?? []) fn(arg);
  }

  return { L, maps, layers, fire };
}
