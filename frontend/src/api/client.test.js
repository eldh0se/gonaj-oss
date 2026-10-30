import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  ApiError,
  getConnectivity,
  getRoute,
  getStop,
  listAllStops,
  listRoutes,
  listStops,
} from "./client.js";

function jsonResponse(body, { status = 200 } = {}) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  };
}

describe("api/client", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
  });

  it("queries routes by search text with pagination", async () => {
    const fetch = vi.fn(async () =>
      jsonResponse({ count: 0, results: [], total_pages: 0 })
    );
    vi.stubGlobal("fetch", fetch);
    await listRoutes({ search: "Fort", page: 2, pageSize: 20 });
    const url = fetch.mock.calls[0][0];
    expect(url).toContain("/api/v1/routes/");
    expect(url).toContain("search=Fort");
    expect(url).toContain("page=2");
    expect(url).toContain("page_size=20");
  });

  it("omits blank search so blank means browse-all", async () => {
    const fetch = vi.fn(async () =>
      jsonResponse({ count: 0, results: [], total_pages: 0 })
    );
    vi.stubGlobal("fetch", fetch);
    await listRoutes({ search: "   ".trim() });
    expect(fetch.mock.calls[0][0]).not.toContain("search=");
    await listStops({});
    expect(fetch.mock.calls[1][0]).not.toContain("search=");
    expect(fetch.mock.calls[1][0]).not.toContain("bbox=");
  });

  it("queries direct connectivity by stop ids", async () => {
    const fetch = vi.fn(async () =>
      jsonResponse({ count: 1, results: [], total_pages: 1 })
    );
    vi.stubGlobal("fetch", fetch);
    await getConnectivity(11, 18);
    const url = fetch.mock.calls[0][0];
    expect(url).toContain("/api/v1/connectivity/");
    expect(url).toContain("from=11");
    expect(url).toContain("to=18");
  });

  it("caps page size at 100", async () => {
    const fetch = vi.fn(async () =>
      jsonResponse({ count: 0, results: [], total_pages: 0 })
    );
    vi.stubGlobal("fetch", fetch);
    await listStops({ bbox: "76.2,9.9,76.35,10.0", pageSize: 5000 });
    expect(fetch.mock.calls[0][0]).toContain("page_size=100");
  });

  it("passes zoom_in and empty envelopes through verbatim", async () => {
    const fetch = vi.fn(async () =>
      jsonResponse({
        count: 0,
        results: [],
        total_pages: 0,
        current_page: 1,
        page_size: 20,
        status: "zoom_in",
        detail: "That area is too large to list stops for.",
      })
    );
    vi.stubGlobal("fetch", fetch);
    const body = await listStops({ bbox: "70,8,80,12" });
    expect(body.status).toBe("zoom_in");
    expect(body.results).toEqual([]);
  });

  it("surfaces the API's plain-language detail on errors", async () => {
    const fetch = vi.fn(async () =>
      jsonResponse(
        { detail: "We could not find that route. Please check the link." },
        { status: 404 }
      )
    );
    vi.stubGlobal("fetch", fetch);
    const err = await getRoute(99999999).catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(404);
    expect(err.detail).toContain("could not find that route");
  });

  it("reports a plain message when the backend is unreachable", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("Failed to fetch");
      })
    );
    const err = await getStop(1).catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(0);
    expect(err.detail).toContain("could not reach");
  });

  it("rethrows aborts so callers can discard stale areas", async () => {
    const abort = new DOMException("Aborted", "AbortError");
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw abort;
      })
    );
    await expect(listRoutes()).rejects.toBe(abort);
  });

  it("follows every page for area queries", async () => {
    const pages = [
      { count: 3, results: [{ id: 1 }], total_pages: 2, current_page: 1 },
      { count: 3, results: [{ id: 2 }, { id: 3 }], total_pages: 2, current_page: 2 },
    ];
    const fetch = vi.fn(async (url) => {
      const page = new URL(url, "http://x").searchParams.get("page");
      return jsonResponse(pages[Number(page) - 1]);
    });
    vi.stubGlobal("fetch", fetch);
    const body = await listAllStops({ bbox: "76.2,9.9,76.35,10.0" });
    expect(body.results.map((s) => s.id)).toEqual([1, 2, 3]);
    expect(fetch).toHaveBeenCalledTimes(2);
  });
});
