import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { postJourney, postTranscribe } from "./journey.js";

function jsonResponse(body, { status = 200 } = {}) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  };
}

describe("api/journey debug logging", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("logs journey network failures in development without the question", async () => {
    vi.stubEnv("DEV", true);
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("down");
      })
    );
    const spy = vi.spyOn(console, "debug").mockImplementation(() => {});
    await expect(
      postJourney({ question: "sweep-marker-question" })
    ).rejects.toMatchObject({ name: "ApiError" });
    expect(spy).toHaveBeenCalledTimes(1);
    const logged = JSON.stringify(spy.mock.calls[0]);
    expect(logged).toContain("/journey/");
    expect(logged).not.toContain("sweep-marker-question");
  });

  it("logs non-ok journey outcomes in development", async () => {
    vi.stubEnv("DEV", true);
    vi.stubGlobal("fetch", async () =>
      jsonResponse({ detail: "Nope." }, { status: 503 })
    );
    const spy = vi.spyOn(console, "debug").mockImplementation(() => {});
    await expect(postJourney({ question: "q" })).rejects.toMatchObject({
      status: 503,
    });
    expect(spy).toHaveBeenCalled();
  });

  it("stays silent outside development", async () => {
    vi.stubEnv("DEV", false);
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("down");
      })
    );
    const spy = vi.spyOn(console, "debug").mockImplementation(() => {});
    await expect(postJourney({ question: "q" })).rejects.toMatchObject({
      name: "ApiError",
    });
    expect(spy).not.toHaveBeenCalled();
  });

  it("logs transcription failures without the audio", async () => {
    vi.stubEnv("DEV", true);
    vi.stubGlobal("fetch", async () =>
      jsonResponse({ detail: "Bad." }, { status: 400 })
    );
    const spy = vi.spyOn(console, "debug").mockImplementation(() => {});
    await expect(
      postTranscribe(new Blob(["sweep-marker-audio"], { type: "audio/webm" }))
    ).rejects.toMatchObject({ status: 400 });
    expect(spy).toHaveBeenCalled();
    const logged = JSON.stringify(spy.mock.calls[0]);
    expect(logged).toContain("transcribe");
    expect(logged).not.toContain("sweep-marker-audio");
  });
});
