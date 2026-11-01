import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App.jsx";

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
});
