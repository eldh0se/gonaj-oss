import { afterEach, describe, expect, it, vi } from "vitest";
import { debugLog } from "./debug.js";

describe("debugLog", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("writes to the console in development", () => {
    vi.stubEnv("DEV", true);
    const spy = vi.spyOn(console, "debug").mockImplementation(() => {});
    debugLog("api", { path: "/api/v1/routes/", outcome: "http-200" });
    expect(spy).toHaveBeenCalledTimes(1);
  });

  it("stays silent outside development", () => {
    vi.stubEnv("DEV", false);
    const spy = vi.spyOn(console, "debug").mockImplementation(() => {});
    debugLog("api", { path: "/api/v1/routes/", outcome: "http-200" });
    expect(spy).not.toHaveBeenCalled();
  });
});
