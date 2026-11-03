import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App.jsx";

vi.mock("./components/MapView.jsx", () => ({
  default: () => <div data-testid="map-container" />,
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
});
