import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import JourneyPanel from "./JourneyPanel.jsx";

const OK_PAYLOAD = {
  status: "ok",
  answer: "Take the South-Fort service from Ernakulam South to Fort Kochi.",
  boarding_stop: { id: 11, name: "Ernakulam South" },
  alighting_stop: { id: 18, name: "Fort Kochi" },
  routes: [{ id: 7, name: "South-Fort", evidence: "/routes/7" }],
  meta: { model: "muse-spark-1.3", provider: "meta", latency_ms: 900 },
};

const REFUSE_PAYLOAD = {
  status: "refuse",
  message: "I could not find a direct service between those stops.",
  meta: { model: "muse-spark-1.3", provider: "meta", latency_ms: 400 },
};

function mockFetch(payload) {
  const fetch = vi.fn(async () => ({ ok: true, json: async () => payload }));
  vi.stubGlobal("fetch", fetch);
  return fetch;
}

describe("JourneyPanel", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("asks a typed question without fetching on mount", () => {
    const fetch = vi.fn(async () => {
      throw new Error("must not be called");
    });
    vi.stubGlobal("fetch", fetch);
    render(<JourneyPanel />);
    expect(
      screen.getByRole("heading", { name: /journey helper/i })
    ).toBeTruthy();
    expect(screen.getByLabelText(/your journey question/i)).toBeTruthy();
    expect(
      screen.getByRole("button", { name: /ask/i })
    ).toBeTruthy();
    expect(globalThis.fetch).not.toHaveBeenCalled();
    vi.unstubAllGlobals();
  });

  it("renders an evidence-grounded answer with a working link", async () => {
    mockFetch(OK_PAYLOAD);
    render(<JourneyPanel />);
    fireEvent.change(screen.getByLabelText(/your journey question/i), {
      target: { value: "How do I get from Ernakulam South to Fort Kochi?" },
    });
    fireEvent.click(screen.getByRole("button", { name: /ask/i }));
    expect(await screen.findByText(/South-Fort service/)).toBeTruthy();
    const link = await screen.findByRole("link", { name: /South-Fort/ });
    expect(link.getAttribute("href")).toBe("/routes/7");
    expect(localStorage.length).toBe(0);
    vi.unstubAllGlobals();
  });

  it("renders a plain refusal with no links", async () => {
    mockFetch(REFUSE_PAYLOAD);
    render(<JourneyPanel />);
    fireEvent.change(screen.getByLabelText(/your journey question/i), {
      target: { value: "How do I get somewhere unknown?" },
    });
    fireEvent.click(screen.getByRole("button", { name: /ask/i }));
    expect(await screen.findByText(/could not find a direct service/i)).toBeTruthy();
    expect(screen.queryByRole("link")).toBeNull();
    vi.unstubAllGlobals();
  });

  it("offers every candidate and asks for a choice", async () => {
    const disambiguate = {
      status: "disambiguate",
      message: "I found more than one stop called North. Which one did you mean?",
      candidates: [
        { id: 201, name: "North Hub" },
        { id: 312, name: "North Edge" },
      ],
      meta: { model: "muse-spark-1.3", provider: "meta", latency_ms: 480 },
    };
    const fetch = vi.fn(async () => ({ ok: true, json: async () => disambiguate }));
    vi.stubGlobal("fetch", fetch);
    render(<JourneyPanel />);
    fireEvent.change(screen.getByLabelText(/your journey question/i), {
      target: { value: "How do I get from North?" },
    });
    fireEvent.click(screen.getByRole("button", { name: /ask/i }));
    expect(await screen.findByText(/which one did you mean/i)).toBeTruthy();
    expect(screen.getByRole("button", { name: "North Hub" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "North Edge" })).toBeTruthy();
    expect(screen.queryByRole("link")).toBeNull();
    vi.unstubAllGlobals();
  });

  it("sends the chosen candidate with its context ids", async () => {
    const disambiguate = {
      status: "disambiguate",
      message: "I found more than one stop called North. Which one did you mean?",
      candidates: [
        { id: 201, name: "North Hub", detail: "10.0500,76.3000" },
        { id: 312, name: "North Edge" },
      ],
      slot: "from",
      resolved: { id: 11, name: "Ernakulam South" },
      offered_ids: [201, 312],
      slots: { from_ids: [201, 312], to_ids: [11] },
      meta: { model: "muse-spark-1.3", provider: "meta", latency_ms: 480 },
    };
    const bodies = [];
    const fetch = vi.fn(async (url, options) => {
      const body = JSON.parse(options.body);
      bodies.push(body);
      const payload =
        bodies.length === 1
          ? disambiguate
          : {
              status: "ok",
              answer: "Take the North service from North Hub onward.",
              boarding_stop: { id: 201, name: "North Hub" },
              alighting_stop: { id: 11, name: "Ernakulam South" },
              routes: [{ id: 9, name: "North run", evidence: "/routes/9" }],
              meta: { model: "muse-spark-1.3", provider: "meta", latency_ms: 500 },
            };
      return { ok: true, json: async () => payload };
    });
    vi.stubGlobal("fetch", fetch);
    render(<JourneyPanel />);
    fireEvent.change(screen.getByLabelText(/your journey question/i), {
      target: { value: "How do I get from North?" },
    });
    fireEvent.click(screen.getByRole("button", { name: /ask/i }));
    fireEvent.click(await screen.findByRole("button", { name: /North Hub/ }));
    expect(await screen.findByText(/North service/)).toBeTruthy();
    expect(bodies).toHaveLength(2);
    expect(bodies[1].context.candidate_stop_ids).toEqual([201, 312]);
    expect(bodies[1].context.selected_stop_id).toBe(201);
    expect(bodies[1].context.slot).toBe("from");
    expect(bodies[1].context.resolved).toEqual({
      id: 11,
      name: "Ernakulam South",
    });
    expect(bodies[1].context.slots).toEqual({
      from_ids: [201, 312],
      to_ids: [11],
    });
    expect(bodies[1].history).toEqual([
      { role: "user", content: "How do I get from North?" },
    ]);
    expect(bodies[1].question).toBe("North Hub");
    vi.unstubAllGlobals();
  });

  it("completes a two-step both-ends flow with surviving context", async () => {
    const first = {
      status: "disambiguate",
      message: "Thanks — keeping Aluva. Which one did you mean for the destination?",
      candidates: [
        { id: 623, name: "Kaloor", detail: "9.9900,76.2900" },
        { id: 624, name: "Kaloor", detail: "9.9800,76.3000" },
      ],
      slot: "to",
      resolved: { id: 621, name: "Aluva" },
      offered_ids: [623, 624],
      slots: { from_ids: [621, 622], to_ids: [623, 624] },
      meta: { model: "none", provider: "local-fallback", latency_ms: 40 },
    };
    const bodies = [];
    const fetch = vi.fn(async (url, options) => {
      const body = JSON.parse(options.body);
      bodies.push(body);
      const payload =
        bodies.length === 1
          ? first
          : {
              status: "ok",
              answer: "Take the A1-K1 service from Aluva to Kaloor.",
              boarding_stop: { id: 621, name: "Aluva" },
              alighting_stop: { id: 623, name: "Kaloor" },
              routes: [{ id: 5, name: "A1-K1", evidence: "/routes/5" }],
              meta: {
                model: "none",
                provider: "local-fallback",
                resolution: "selection",
                latency_ms: 42,
              },
            };
      return { ok: true, json: async () => payload };
    });
    vi.stubGlobal("fetch", fetch);
    render(<JourneyPanel />);
    fireEvent.change(screen.getByLabelText(/your journey question/i), {
      target: { value: "How do I get from Aluva to Kaloor?" },
    });
    fireEvent.click(screen.getByRole("button", { name: /ask/i }));
    const options = await screen.findAllByRole("button", { name: /Kaloor/ });
    expect(options).toHaveLength(2);
    fireEvent.click(options[0]);
    expect(await screen.findByText(/A1-K1 service/)).toBeTruthy();
    expect(bodies).toHaveLength(2);
    expect(bodies[1].context.selected_stop_id).toBe(623);
    expect(bodies[1].context.slot).toBe("to");
    expect(bodies[1].context.resolved).toEqual({ id: 621, name: "Aluva" });
    expect(bodies[1].history).toEqual([
      { role: "user", content: "How do I get from Aluva to Kaloor?" },
    ]);
    vi.unstubAllGlobals();
  });

  it("says plainly when voice input is unavailable", async () => {
    render(<JourneyPanel />);
    fireEvent.pointerDown(screen.getByRole("button", { name: /dictate/i }));
    expect(await screen.findByText(/voice input is not available/i)).toBeTruthy();
  });

  it("fills the transcript from dictation and sends the edited text", async () => {
    const bodies = [];
    const fetch = vi.fn(async (url, options) => {
      if (url.includes("transcribe")) {
        return { ok: true, json: async () => ({ transcript: "dictated words" }) };
      }
      const body = JSON.parse(options.body);
      bodies.push(body);
      return {
        ok: true,
        json: async () => ({
          status: "refuse",
          message: "I could not find a direct service between those stops.",
          meta: { model: "muse-spark-1.3", provider: "meta", latency_ms: 300 },
        }),
      };
    });
    vi.stubGlobal("fetch", fetch);

    const tracks = [{ stop: vi.fn() }];
    const stream = { getTracks: () => tracks };
    Object.defineProperty(globalThis.navigator, "mediaDevices", {
      value: { getUserMedia: vi.fn(async () => stream) },
      configurable: true,
    });
    let recorder = null;
    class MockRecorder {
      constructor(streamArg, options) {
        this.stream = streamArg;
        this.state = "inactive";
        recorder = this;
      }
      start() {
        this.state = "recording";
      }
      stop() {
        this.state = "inactive";
        this.ondataavailable?.({
          data: new Blob(["audio-bytes"], { type: "audio/webm" }),
        });
        this.onstop?.();
      }
    }
    vi.stubGlobal("MediaRecorder", MockRecorder);

    render(<JourneyPanel />);
    const dictate = screen.getByRole("button", { name: /dictate/i });
    fireEvent.pointerDown(dictate);
    await screen.findByText(/listening/i);
    fireEvent.pointerUp(dictate);
    expect(await screen.findByDisplayValue("dictated words")).toBeTruthy();

    fireEvent.change(screen.getByLabelText(/your journey question/i), {
      target: { value: "edited words" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^ask$/i }));
    await screen.findByText(/could not find a direct service/i);
    expect(bodies).toHaveLength(1);
    expect(bodies[0].question).toBe("edited words");
    expect(tracks[0].stop).toHaveBeenCalled();
    vi.unstubAllGlobals();
  });

  it("labels answers as unverified AI output", async () => {
    mockFetch(OK_PAYLOAD);
    render(<JourneyPanel />);
    fireEvent.change(screen.getByLabelText(/your journey question/i), {
      target: { value: "How do I get there?" },
    });
    fireEvent.click(screen.getByRole("button", { name: /ask/i }));
    const label = await screen.findByText(/unverified ai answer/i);
    expect(label.className).toMatch(/gonaj-unverified/);
    vi.unstubAllGlobals();
  });

  it("labels refusals with the same unverified family", async () => {
    mockFetch(REFUSE_PAYLOAD);
    render(<JourneyPanel />);
    fireEvent.change(screen.getByLabelText(/your journey question/i), {
      target: { value: "How do I get nowhere?" },
    });
    fireEvent.click(screen.getByRole("button", { name: /ask/i }));
    await screen.findByText(/could not find a direct service/i);
    expect(screen.getByText(/unverified/i)).toBeTruthy();
    vi.unstubAllGlobals();
  });

  it("finds direct routes between picked stops", async () => {
    const fetch = vi.fn(async (url) => {
      if (url.includes("/connectivity/")) {
        return {
          ok: true,
          json: async () => ({
            count: 1,
            results: [
              { id: 1, name: "South-Fort", evidence: "/api/v1/routes/1/" },
            ],
            total_pages: 1,
          }),
        };
      }
      const isFort = url.includes("Fort");
      return {
        ok: true,
        json: async () => ({
          results: isFort
            ? [{ id: 18, name: "Fort Kochi" }]
            : [{ id: 11, name: "Ernakulam South" }],
          count: 1,
          total_pages: 1,
        }),
      };
    });
    vi.stubGlobal("fetch", fetch);
    render(<JourneyPanel />);
    fireEvent.change(screen.getByLabelText(/from stop/i), {
      target: { value: "Ernakulam" },
    });
    fireEvent.click(await screen.findByRole("button", { name: "Ernakulam South" }));
    fireEvent.change(screen.getByLabelText(/to stop/i, { selector: "input" }), {
      target: { value: "Fort" },
    });
    fireEvent.click(await screen.findByRole("button", { name: "Fort Kochi" }));
    const toBox = screen.getByLabelText(/to stop/i, { selector: "input" });
    expect(toBox.value).toBe("Fort Kochi");
    expect(toBox.closest(".gonaj-stop-picker").className).toMatch(/is-picked/);
    fireEvent.click(screen.getByRole("button", { name: /clear to stop/i }));
    expect(screen.getByLabelText(/to stop/i, { selector: "input" }).value).toBe("");
    fireEvent.change(screen.getByLabelText(/to stop/i, { selector: "input" }), { target: { value: "Fort" } });
    fireEvent.click(await screen.findByRole("button", { name: "Fort Kochi" }));
    fireEvent.click(screen.getByRole("button", { name: /find direct routes/i }));
    const link = await screen.findByRole("link", { name: "South-Fort" });
    expect(link.getAttribute("href")).toBe("/routes/1");
    const connUrl = fetch.mock.calls.find(([u]) => u.includes("/connectivity/"))[0];
    expect(connUrl).toContain("from=11");
    expect(connUrl).toContain("to=18");
    vi.unstubAllGlobals();
  });

  it("says plainly when no direct service connects the picked stops", async () => {
    const fetch = vi.fn(async (url) => {
      if (url.includes("/connectivity/")) {
        return {
          ok: true,
          json: async () => ({ count: 0, results: [], total_pages: 1 }),
        };
      }
      const name = url.includes("Lonely") ? "Lonely Point" : "Ernakulam South";
      const id = url.includes("Lonely") ? 503 : 11;
      return {
        ok: true,
        json: async () => ({ results: [{ id, name }], count: 1, total_pages: 1 }),
      };
    });
    vi.stubGlobal("fetch", fetch);
    render(<JourneyPanel />);
    fireEvent.change(screen.getByLabelText(/from stop/i), {
      target: { value: "Ernakulam" },
    });
    fireEvent.click(await screen.findByRole("button", { name: "Ernakulam South" }));
    fireEvent.change(screen.getByLabelText(/to stop/i, { selector: "input" }), {
      target: { value: "Lonely" },
    });
    fireEvent.click(await screen.findByRole("button", { name: "Lonely Point" }));
    fireEvent.click(screen.getByRole("button", { name: /find direct routes/i }));
    expect(await screen.findByText(/could not find a direct service/i)).toBeTruthy();
    expect(screen.queryByRole("link")).toBeNull();
    vi.unstubAllGlobals();
  });

  it("keeps only one result active at a time", async () => {
    const fetch = vi.fn(async (url, options) => {
      if (url.includes("/connectivity/")) {
        return {
          ok: true,
          json: async () => ({
            count: 1,
            results: [{ id: 1, name: "South-Fort" }],
            total_pages: 1,
          }),
        };
      }
      if (url.includes("/api/v1/journey/")) {
        return {
          ok: true,
          json: async () => ({
            status: "ok",
            answer: "Take the South-Fort service.",
            boarding_stop: { id: 11, name: "Ernakulam South" },
            alighting_stop: { id: 18, name: "Fort Kochi" },
            routes: [{ id: 1, name: "South-Fort", evidence: "/routes/1" }],
            meta: { model: "muse-spark-1.3", provider: "meta", latency_ms: 300 },
          }),
        };
      }
      return {
        ok: true,
        json: async () => ({ results: [{ id: 11, name: "Ernakulam South" }], count: 1, total_pages: 1 }),
      };
    });
    vi.stubGlobal("fetch", fetch);
    render(<JourneyPanel />);
    fireEvent.change(screen.getByLabelText(/from stop/i, { selector: "input" }), {
      target: { value: "Ernakulam" },
    });
    fireEvent.click(await screen.findByRole("button", { name: "Ernakulam South" }));
    fireEvent.change(screen.getByLabelText(/to stop/i, { selector: "input" }), {
      target: { value: "Ernakulam" },
    });
    const picks = await screen.findAllByRole("button", { name: "Ernakulam South" });
    fireEvent.click(picks[picks.length - 1]);
    fireEvent.click(screen.getByRole("button", { name: /find direct routes/i }));
    await screen.findByRole("link", { name: "South-Fort" });

    fireEvent.change(screen.getByLabelText(/your journey question/i), {
      target: { value: "How do I get there?" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^ask$/i }));
    await screen.findByText(/Take the South-Fort service/);
    const links = screen.getAllByRole("link", { name: "South-Fort" });
    expect(links).toHaveLength(1);
    expect(links[0].closest(".gonaj-journey-results")).toBeTruthy();
    expect(links[0].closest("article")).toBeTruthy();
    vi.unstubAllGlobals();
  });

  it("reports helper outages in plain language", async () => {
    const fetch = vi.fn(async () => {
      throw new Error("network down");
    });
    vi.stubGlobal("fetch", fetch);
    render(<JourneyPanel />);
    fireEvent.change(screen.getByLabelText(/your journey question/i), {
      target: { value: "How do I get there?" },
    });
    fireEvent.click(screen.getByRole("button", { name: /ask/i }));
    expect(await screen.findByText(/cannot answer right now/i)).toBeTruthy();
    vi.unstubAllGlobals();
  });
});
