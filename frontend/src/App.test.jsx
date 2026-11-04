import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { useEffect } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App.jsx";

const { mapProbe } = vi.hoisted(() => ({ mapProbe: { props: null } }));

vi.mock("./components/MapView.jsx", () => ({
  default: (props) => {
    mapProbe.props = props;
    const onAreaChange = props.onAreaChange;
    useEffect(() => {
      onAreaChange?.({ west: 76.2, south: 9.9, east: 76.35, north: 10.0 });
    }, [onAreaChange]);
    return <div data-testid="map-container" />;
  },
}));

function stubFetch() {
  const fetch = vi.fn(async (url) => {
    if (String(url).includes("/api/v1/journey/")) {
      return {
        ok: true,
        json: async () => ({
          status: "refuse",
          message: "Please ask me a journey question.",
          meta: { model: "muse-spark-1.3", provider: "meta", latency_ms: 5 },
        }),
      };
    }
    return {
      ok: true,
      json: async () => ({
        results: [],
        count: 0,
        total_pages: 1,
        current_page: 1,
      }),
    };
  });
  vi.stubGlobal("fetch", fetch);
  return fetch;
}

describe("App map page", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
  });

  it("mounts the map with an opt-in locator that stays off by default", async () => {
    const getCurrentPosition = vi.fn();
    Object.defineProperty(globalThis.navigator, "geolocation", {
      value: { getCurrentPosition },
      configurable: true,
    });
    stubFetch();
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>
    );
    expect(await screen.findByTestId("map-container")).toBeTruthy();
    expect(
      screen.getByRole("button", { name: /show my location/i })
    ).toBeTruthy();
    expect(getCurrentPosition).not.toHaveBeenCalled();
    vi.unstubAllGlobals();
    // @ts-ignore jsdom cleanup
    delete globalThis.navigator.geolocation;
  });

  it("locates only after explicit opt-in", async () => {
    const getCurrentPosition = vi.fn((success) =>
      success({ coords: { latitude: 9.97, longitude: 76.28 } })
    );
    Object.defineProperty(globalThis.navigator, "geolocation", {
      value: { getCurrentPosition },
      configurable: true,
    });
    stubFetch();
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>
    );
    fireEvent.click(
      await screen.findByRole("button", { name: /show my location/i })
    );
    expect(getCurrentPosition).toHaveBeenCalledTimes(1);
    vi.unstubAllGlobals();
    // @ts-ignore jsdom cleanup
    delete globalThis.navigator.geolocation;
  });

  it("retains journey results after the route overlay is closed", async () => {
    const journeyPayload = {
      status: "ok",
      answer: "Take R7 from Kaloor to Fort Kochi.",
      options: [
        {
          route: { id: 7, name: "R7", evidence: "/routes/7" },
          boarding_stop: { id: 11, name: "Kaloor" },
          alighting_stop: { id: 19, name: "Fort Kochi" },
          operator: "City Private",
          network: "City",
          stop_count: 12,
          also_nearby_boarding: [],
          also_nearby: [],
          overflow_nearby_boarding: 0,
          overflow_nearby: 0,
        },
      ],
      total_options: 1,
      total_pages: 1,
      page: 1,
      page_size: 5,
      destinations: [],
      meta: { model: "muse-spark-1.3", provider: "meta", latency_ms: 900 },
    };
    const fetch = vi.fn(async (url) => {
      const target = String(url);
      if (target.includes("/api/v1/journey/")) {
        return { ok: true, json: async () => journeyPayload };
      }
      if (target.includes("/routes/7/")) {
        return {
          ok: true,
          json: async () => ({
            id: 7,
            name: "R7",
            stops: [
              { stop: { id: 11, name: "Kaloor", lat: 9.97, lon: 76.28 } },
            ],
          }),
        };
      }
      if (target.includes("/api/v1/routes/")) {
        return {
          ok: true,
          json: async () => ({
            results: [{ id: 7, name: "R7" }],
            count: 1,
            total_pages: 1,
            current_page: 1,
          }),
        };
      }
      return {
        ok: true,
        json: async () => ({
          results: [],
          count: 0,
          total_pages: 1,
          current_page: 1,
        }),
      };
    });
    vi.stubGlobal("fetch", fetch);
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>
    );
    await screen.findByRole("tab", { name: "Journey" });
    fireEvent.change(screen.getByLabelText(/your journey question/i), {
      target: { value: "How do I get from Kaloor to Fort Kochi?" },
    });
    fireEvent.click(screen.getByRole("button", { name: /ask/i }));
    expect(
      await screen.findByText("Take R7 from Kaloor to Fort Kochi.")
    ).toBeTruthy();
    fireEvent.click(screen.getByRole("link", { name: "R7" }));
    expect(await screen.findByLabelText("Route detail")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /close/i }));
    expect(screen.queryByLabelText("Route detail")).toBeNull();
    expect(
      screen.getByText("Take R7 from Kaloor to Fort Kochi.")
    ).toBeTruthy();
    vi.unstubAllGlobals();
  });

  it("retains direct-route results after the route overlay is closed", async () => {
    const fetch = vi.fn(async (url) => {
      const target = String(url);
      if (target.includes("/connectivity/")) {
        return {
          ok: true,
          json: async () => ({ results: [{ id: 7, name: "R7" }] }),
        };
      }
      if (target.includes("/routes/7/")) {
        return {
          ok: true,
          json: async () => ({
            id: 7,
            name: "R7",
            stops: [
              { stop: { id: 11, name: "Kaloor", lat: 9.97, lon: 76.28 } },
            ],
          }),
        };
      }
      if (target.includes("/api/v1/routes/")) {
        return {
          ok: true,
          json: async () => ({
            results: [{ id: 7, name: "R7" }],
            count: 1,
            total_pages: 1,
            current_page: 1,
          }),
        };
      }
      if (target.includes("/api/v1/stops/") && target.includes("search=")) {
        return {
          ok: true,
          json: async () => ({
            results: [
              { id: 11, name: "Kaloor" },
              { id: 19, name: "Fort Kochi" },
            ],
            count: 2,
            total_pages: 1,
            current_page: 1,
          }),
        };
      }
      return {
        ok: true,
        json: async () => ({
          results: [],
          count: 0,
          total_pages: 1,
          current_page: 1,
        }),
      };
    });
    vi.stubGlobal("fetch", fetch);
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>
    );
    await screen.findByRole("tab", { name: "Journey" });
    fireEvent.change(screen.getByLabelText(/from stop/i), {
      target: { value: "Kaloor" },
    });
    fireEvent.click(await screen.findByRole("button", { name: "Kaloor" }));
    fireEvent.change(screen.getByLabelText(/to stop/i), {
      target: { value: "Fort Kochi" },
    });
    fireEvent.click(await screen.findByRole("button", { name: "Fort Kochi" }));
    fireEvent.click(
      screen.getByRole("button", { name: /find direct routes/i })
    );
    fireEvent.click(await screen.findByRole("link", { name: "R7" }));
    expect(await screen.findByLabelText("Route detail")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /close/i }));
    expect(screen.queryByLabelText("Route detail")).toBeNull();
    expect(screen.getByRole("link", { name: "R7" })).toBeTruthy();
    vi.unstubAllGlobals();
  });

  it("shows the footer version with metadata and falls back without", async () => {
    stubFetch();
    globalThis.__APP_VERSION__ = "0.1.0";
    globalThis.__APP_SHA__ = "abcdef123456";
    globalThis.__APP_BUILT_AT__ = "2026-11-04T02:00:00Z";
    const first = render(
      <MemoryRouter>
        <App />
      </MemoryRouter>
    );
    expect((await first.findByTestId("app-version")).textContent).toBe(
      "v0.1.0+abcdef1 · built 2026-11-04T02:00:00Z"
    );
    expect(first.container.querySelector("footer.gonaj-version")).toBeTruthy();
    first.unmount();
    globalThis.__APP_VERSION__ = undefined;
    globalThis.__APP_SHA__ = undefined;
    globalThis.__APP_BUILT_AT__ = undefined;
    const second = render(
      <MemoryRouter>
        <App />
      </MemoryRouter>
    );
    expect((await second.findByTestId("app-version")).textContent).toBe("v0.1.0");
    second.unmount();
    vi.unstubAllGlobals();
  });

  it("closing the route overlay restores the previously visible tab", async () => {
    const fetch = vi.fn(async (url) => {
      const target = String(url);
      if (target.includes("/api/v1/routes/7/")) {
        return {
          ok: true,
          json: async () => ({ id: 7, name: "R7", stops: [] }),
        };
      }
      if (target.includes("/api/v1/routes/")) {
        return {
          ok: true,
          json: async () => ({
            results: [{ id: 7, name: "R7" }],
            count: 1,
            total_pages: 1,
            current_page: 1,
          }),
        };
      }
      return {
        ok: true,
        json: async () => ({
          results: [],
          count: 0,
          total_pages: 1,
          current_page: 1,
        }),
      };
    });
    vi.stubGlobal("fetch", fetch);
    render(
      <MemoryRouter initialEntries={["/routes/7"]}>
        <App />
      </MemoryRouter>
    );
    // Overlay opens on top; the Journey tab underneath stays selected.
    expect(await screen.findByRole("heading", { name: "R7" })).toBeTruthy();
    expect(
      screen.getByRole("tab", { name: "Journey" }).getAttribute("aria-selected")
    ).toBe("true");
    expect(screen.getByText(/plain-language answers/i)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /^close$/i }));
    // Close restores the tab content with no search state lost.
    expect(screen.queryByRole("heading", { name: "R7" })).toBeNull();
    expect(
      screen.getByRole("tab", { name: "Journey" }).getAttribute("aria-selected")
    ).toBe("true");
    expect(screen.getByText(/plain-language answers/i)).toBeTruthy();
    vi.unstubAllGlobals();
  });

  it("focuses the map on the selected route and restores markers on close", async () => {
    const areaStops = [
      { id: 11, name: "Kaloor", lat: 9.99, lon: 76.28 },
      { id: 19, name: "Palarivattom", lat: 9.995, lon: 76.29 },
    ];
    const fetch = vi.fn(async (url) => {
      const target = String(url);
      if (target.includes("/api/v1/routes/7/")) {
        return {
          ok: true,
          json: async () => ({
            id: 7,
            name: "R7",
            stops: [
              { stop: { id: 1, name: "Ernakulam South", lat: 9.97, lon: 76.28 }, position: 1, is_origin: true, is_terminus: false },
              { stop: { id: 2, name: "Marine Drive", lat: 9.975, lon: 76.285 }, position: 2, is_origin: false, is_terminus: false },
              { stop: { id: 3, name: "Fort Kochi", lat: 9.96, lon: 76.24 }, position: 3, is_origin: false, is_terminus: true },
            ],
          }),
        };
      }
      if (target.includes("/api/v1/routes/")) {
        return {
          ok: true,
          json: async () => ({
            results: [{ id: 7, name: "R7", origin: "Ernakulam South", destination: "Fort Kochi" }],
            count: 1,
            total_pages: 1,
            current_page: 1,
          }),
        };
      }
      if (target.includes("bbox=")) {
        return {
          ok: true,
          json: async () => ({
            results: areaStops,
            count: areaStops.length,
            total_pages: 1,
            current_page: 1,
          }),
        };
      }
      return {
        ok: true,
        json: async () => ({
          results: [],
          count: 0,
          total_pages: 1,
          current_page: 1,
        }),
      };
    });
    vi.stubGlobal("fetch", fetch);
    mapProbe.props = null;
    render(
      <MemoryRouter initialEntries={["/routes/7"]}>
        <App />
      </MemoryRouter>
    );
    expect(await screen.findByRole("heading", { name: "R7" })).toBeTruthy();
    // Only the route's stops render; area markers hide; bounds fit the route.
    expect(mapProbe.props.markers.map((m) => m.id)).toEqual([1, 2, 3]);
    expect(mapProbe.props.markers.map((m) => m.role)).toEqual([
      "origin",
      undefined,
      "terminus",
    ]);
    expect(mapProbe.props.highlight).toEqual([
      [9.97, 76.28],
      [9.975, 76.285],
      [9.96, 76.24],
    ]);
    expect(mapProbe.props.fitBounds).toEqual({
      south: 9.96,
      west: 76.24,
      north: 9.975,
      east: 76.285,
    });
    fireEvent.click(screen.getByRole("button", { name: /^close$/i }));
    // Close restores the generic area markers and clears the highlight.
    expect(screen.queryByRole("heading", { name: "R7" })).toBeNull();
    await waitFor(() => expect(mapProbe.props.markers).toEqual(areaStops));
    expect(mapProbe.props.highlight).toBeNull();
    vi.unstubAllGlobals();
  });

  it("centres on a stop card while area markers stay", async () => {
    const areaStops = [
      { id: 11, name: "Kaloor", lat: 9.99, lon: 76.28 },
      { id: 19, name: "Palarivattom", lat: 9.995, lon: 76.29 },
    ];
    const fetch = vi.fn(async (url) => {
      const target = String(url);
      if (target.includes("/api/v1/stops/11/")) {
        return {
          ok: true,
          json: async () => ({ id: 11, name: "Kaloor", serving_routes: [] }),
        };
      }
      if (target.includes("bbox=") || target.includes("/api/v1/stops/")) {
        return {
          ok: true,
          json: async () => ({
            results: areaStops,
            count: areaStops.length,
            total_pages: 1,
            current_page: 1,
          }),
        };
      }
      return {
        ok: true,
        json: async () => ({
          results: [],
          count: 0,
          total_pages: 1,
          current_page: 1,
        }),
      };
    });
    vi.stubGlobal("fetch", fetch);
    mapProbe.props = null;
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>
    );
    fireEvent.click(await screen.findByRole("tab", { name: "Stops" }));
    fireEvent.click(await screen.findByRole("button", { name: "Kaloor" }));
    expect(await screen.findByLabelText("Selected stop")).toBeTruthy();
    expect(mapProbe.props.center).toMatchObject({ lat: 9.99, lon: 76.28 });
    expect(mapProbe.props.markers).toEqual(areaStops);
    vi.unstubAllGlobals();
  });
});
