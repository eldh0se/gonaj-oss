import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import SearchBox from "./SearchBox.jsx";
import ResultsList from "./ResultsList.jsx";

describe("SearchBox", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("emits debounced queries and never calls the network itself", () => {
    vi.useFakeTimers();
    const fetch = vi.fn(async () => {
      throw new Error("must not be called");
    });
    vi.stubGlobal("fetch", fetch);
    const onQuery = vi.fn();
    render(<SearchBox onQuery={onQuery} />);

    // Mount emits the initial blank query (browse-all).
    act(() => {
      vi.advanceTimersByTime(300);
    });
    expect(onQuery).toHaveBeenCalledWith("");

    fireEvent.change(screen.getByLabelText(/search routes and stops/i), {
      target: { value: "For" },
    });
    fireEvent.change(screen.getByLabelText(/search routes and stops/i), {
      target: { value: "Fort" },
    });
    expect(onQuery).toHaveBeenCalledTimes(1);
    act(() => {
      vi.advanceTimersByTime(300);
    });
    expect(onQuery).toHaveBeenCalledTimes(2);
    expect(onQuery).toHaveBeenLastCalledWith("Fort");
    expect(fetch).not.toHaveBeenCalled();
    vi.unstubAllGlobals();
  });
});

const ROUTES = [
  { id: 17, name: "Ernakulam — Fort Kochi", origin: "Ernakulam", destination: "Fort Kochi", operator: "KSRTC", network: null },
  { id: 18, name: null, origin: "Aluva", destination: "Angamaly", operator: null, network: null },
];
const STOPS = [{ id: 101, name: "Ernakulam South", name_ml: null, lat: 9.968, lon: 76.29 }];

describe("ResultsList", () => {
  it("renders loading, error, no-match, and empty states plainly", () => {
    const noop = () => {};
    const { rerender } = render(
      <ResultsList routes={[]} stops={[]} state="loading" errorDetail="" onSelectRoute={noop} onSelectStop={noop} />
    );
    expect(screen.getByRole("status").textContent).toMatch(/searching/i);

    rerender(
      <ResultsList routes={[]} stops={[]} state="error" errorDetail="Search cannot load right now." onSelectRoute={noop} onSelectStop={noop} />
    );
    expect(screen.getByRole("alert").textContent).toMatch(/cannot load/);

    rerender(
      <ResultsList routes={[]} stops={[]} state="no-match" errorDetail="" onSelectRoute={noop} onSelectStop={noop} />
    );
    expect(screen.getByRole("status").textContent).toMatch(/nothing matched/i);

    rerender(
      <ResultsList routes={[]} stops={[]} state="empty" errorDetail="" onSelectRoute={noop} onSelectStop={noop} />
    );
    expect(screen.getByRole("status").textContent).toMatch(/no routes or stops/i);
  });

  it("lists matching routes and stops with plain fallbacks, wiring picks", () => {
    const onSelectRoute = vi.fn();
    const onSelectStop = vi.fn();
    render(
      <ResultsList routes={ROUTES} stops={STOPS} state="ok" errorDetail="" onSelectRoute={onSelectRoute} onSelectStop={onSelectStop} />
    );
    fireEvent.click(screen.getByRole("button", { name: /Ernakulam — Fort Kochi/ }));
    expect(onSelectRoute).toHaveBeenCalledWith(17);
    // Null names fall back to origin — destination, never a blank label.
    fireEvent.click(screen.getByRole("button", { name: /Aluva — Angamaly/ }));
    expect(onSelectRoute).toHaveBeenCalledWith(18);
    fireEvent.click(screen.getByRole("button", { name: /Ernakulam South/ }));
    expect(onSelectStop).toHaveBeenCalledWith(STOPS[0]);
  });
});
