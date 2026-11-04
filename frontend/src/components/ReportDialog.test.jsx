import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi, afterEach } from "vitest";
import ReportDialog from "./ReportDialog.jsx";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("ReportDialog", () => {
  it("opens with the route chip and files the report", async () => {
    const fetch = vi.fn(async () => ({
      ok: true,
      json: async () => ({ reference: "FB-ABC12345", receipt: "received" }),
    }));
    vi.stubGlobal("fetch", fetch);
    const onClose = vi.fn();
    render(
      <ReportDialog
        open
        context={{ route: { id: 7, name: "R7" } }}
        onClose={onClose}
      />
    );
    expect(screen.getByText("Route: R7")).toBeTruthy();
    fireEvent.change(screen.getByLabelText(/category/i), {
      target: { value: "incorrect" },
    });
    fireEvent.change(screen.getByLabelText(/message/i), {
      target: { value: "Wrong terminus." },
    });
    fireEvent.click(screen.getByRole("button", { name: /send report/i }));
    expect(await screen.findByTestId("feedback-receipt")).toBeTruthy();
    expect(screen.getByText(/FB-ABC12345/)).toBeTruthy();
    expect(fetch.mock.calls[0][0]).toBe("/api/v1/feedback/");
    vi.unstubAllGlobals();
  });

  it("renders nothing when closed", () => {
    const { container } = render(
      <ReportDialog open={false} context={{}} onClose={() => {}} />
    );
    expect(container.textContent).toBe("");
  });

  it("opens chipless with no search box and files a general report", async () => {
    const posts = [];
    const fetch = vi.fn(async (url, init) => {
      if (String(url).includes("/feedback/")) {
        posts.push(JSON.parse(init.body));
      }
      return {
        ok: true,
        json: async () => ({ reference: "FB-GENERAL01", receipt: "received" }),
      };
    });
    vi.stubGlobal("fetch", fetch);
    render(<ReportDialog open context={{}} onClose={() => {}} />);
    // Chipless open: no chips and no attach search.
    expect(screen.queryByText(/^(Route|Stop):/)).toBeNull();
    expect(screen.queryByLabelText(/attach/i)).toBeNull();
    // General (chipless) submit returns a receipt.
    fireEvent.change(screen.getByLabelText(/category/i), {
      target: { value: "other" },
    });
    fireEvent.change(screen.getByLabelText(/message/i), {
      target: { value: "General remark." },
    });
    fireEvent.click(screen.getByRole("button", { name: /send report/i }));
    expect(await screen.findByTestId("feedback-receipt")).toBeTruthy();
    expect(screen.getByText(/FB-GENERAL01/)).toBeTruthy();
    expect(posts).toHaveLength(1);
    expect(posts[0].route_id).toBeUndefined();
    expect(posts[0].stop_id).toBeUndefined();
  });

  it("blocks empty submit with inline validation and no request", () => {
    const fetch = vi.fn(async () => ({
      ok: true,
      json: async () => ({}),
    }));
    vi.stubGlobal("fetch", fetch);
    render(<ReportDialog open context={{}} onClose={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: /send report/i }));
    expect(screen.getByRole("alert").textContent).toMatch(/category/i);
    expect(fetch).not.toHaveBeenCalled();
  });

  it("shows a 400 with the draft preserved and retry succeeds", async () => {
    let attempt = 0;
    const fetch = vi.fn(async (url) => {
      if (!String(url).includes("/feedback/")) {
        return { ok: true, json: async () => ({ items: [] }) };
      }
      attempt += 1;
      if (attempt === 1) {
        return {
          ok: false,
          status: 400,
          json: async () => ({ detail: "Please write a message." }),
        };
      }
      return {
        ok: true,
        json: async () => ({ reference: "FB-RETRY001", receipt: "received" }),
      };
    });
    vi.stubGlobal("fetch", fetch);
    render(<ReportDialog open context={{}} onClose={() => {}} />);
    fireEvent.change(screen.getByLabelText(/category/i), {
      target: { value: "missing" },
    });
    fireEvent.change(screen.getByLabelText(/message/i), {
      target: { value: "Stop sign gone." },
    });
    fireEvent.click(screen.getByRole("button", { name: /send report/i }));
    expect(await screen.findByText("Please write a message.")).toBeTruthy();
    // Draft preserved after the failure.
    expect(screen.getByLabelText(/message/i).value).toBe("Stop sign gone.");
    fireEvent.click(screen.getByTestId("feedback-retry"));
    expect(await screen.findByTestId("feedback-receipt")).toBeTruthy();
    expect(screen.getByText(/FB-RETRY001/)).toBeTruthy();
  });

  it("explains a 429 busy response with the draft preserved", async () => {
    const fetch = vi.fn(async (url) => {
      if (!String(url).includes("/feedback/")) {
        return { ok: true, json: async () => ({ items: [] }) };
      }
      return {
        ok: false,
        status: 429,
        json: async () => ({ detail: "Too many requests. Please wait." }),
      };
    });
    vi.stubGlobal("fetch", fetch);
    render(<ReportDialog open context={{}} onClose={() => {}} />);
    fireEvent.change(screen.getByLabelText(/category/i), {
      target: { value: "other" },
    });
    fireEvent.change(screen.getByLabelText(/message/i), {
      target: { value: "Busy test." },
    });
    fireEvent.click(screen.getByRole("button", { name: /send report/i }));
    expect(await screen.findByText(/too many requests/i)).toBeTruthy();
    expect(screen.getByLabelText(/message/i).value).toBe("Busy test.");
  });

  it("sends one request on double-tap while pending", async () => {
    let release;
    const gate = new Promise((resolve) => {
      release = resolve;
    });
    const fetch = vi.fn(async (url) => {
      if (!String(url).includes("/feedback/")) {
        return { ok: true, json: async () => ({ items: [] }) };
      }
      await gate;
      return {
        ok: true,
        json: async () => ({ reference: "FB-ONCE0001", receipt: "received" }),
      };
    });
    vi.stubGlobal("fetch", fetch);
    render(<ReportDialog open context={{}} onClose={() => {}} />);
    fireEvent.change(screen.getByLabelText(/category/i), {
      target: { value: "incorrect" },
    });
    fireEvent.change(screen.getByLabelText(/message/i), {
      target: { value: "Double tap." },
    });
    const send = screen.getByRole("button", { name: /send report/i });
    fireEvent.click(send);
    fireEvent.click(send);
    expect(fetch.mock.calls.filter(([url]) => String(url).includes("/feedback/"))).toHaveLength(1);
    release();
    expect(await screen.findByTestId("feedback-receipt")).toBeTruthy();
  });

  it("traps focus in on open and returns it to the invoker on close", async () => {
    const invoker = document.createElement("button");
    invoker.textContent = "invoker";
    document.body.appendChild(invoker);
    invoker.focus();
    try {
      const onClose = vi.fn();
      const { rerender } = render(
        <ReportDialog open context={{}} onClose={onClose} />
      );
      await vi.waitFor(() => {
        expect(document.activeElement?.getAttribute("role")).toBe("dialog");
      });
      rerender(<ReportDialog open={false} context={{}} onClose={onClose} />);
      expect(document.activeElement).toBe(invoker);
    } finally {
      invoker.remove();
    }
  });

  it("closes on Escape and ignores Escape and backdrop while pending", async () => {
    let release;
    const gate = new Promise((resolve) => {
      release = resolve;
    });
    const fetch = vi.fn(async (url) => {
      if (!String(url).includes("/feedback/")) {
        return { ok: true, json: async () => ({ items: [] }) };
      }
      await gate;
      return {
        ok: true,
        json: async () => ({ reference: "FB-GUARD001", receipt: "received" }),
      };
    });
    vi.stubGlobal("fetch", fetch);
    // Idle Escape closes.
    const onClose = vi.fn();
    const { unmount } = render(
      <ReportDialog open context={{}} onClose={onClose} />
    );
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
    unmount();
    // Pending Escape and backdrop do not close.
    const onClosePending = vi.fn();
    render(<ReportDialog open context={{}} onClose={onClosePending} />);
    fireEvent.change(screen.getByLabelText(/category/i), {
      target: { value: "outdated" },
    });
    fireEvent.change(screen.getByLabelText(/message/i), {
      target: { value: "Guard test." },
    });
    fireEvent.click(screen.getByRole("button", { name: /send report/i }));
    await vi.waitFor(() => {
      expect(screen.getByRole("button", { name: /sending/i })).toBeTruthy();
    });
    fireEvent.keyDown(document, { key: "Escape" });
    fireEvent.click(screen.getByTestId("feedback-scrim"));
    expect(onClosePending).not.toHaveBeenCalled();
    release();
    expect(await screen.findByTestId("feedback-receipt")).toBeTruthy();
    // Idle backdrop closes.
    fireEvent.click(screen.getByTestId("feedback-scrim"));
    expect(onClosePending).toHaveBeenCalledTimes(1);
  });
});
