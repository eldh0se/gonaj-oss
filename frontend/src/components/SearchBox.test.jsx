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
const ROUTE_LIST = { items: ROUTES, page: 1, totalPages: 1, count: 2 };
const STOP_LIST = { items: STOPS, page: 1, totalPages: 1, count: 1 };
const EMPTY_LIST = { items: [], page: 1, totalPages: 1, count: 0 };

describe("ResultsList", () => {
  it("renders loading, error, no-match, and empty states plainly", () => {
    const noop = () => {};
    const { rerender } = render(
      <ResultsList routeList={EMPTY_LIST} stopList={EMPTY_LIST} state="loading" errorDetail="" onSelectRoute={noop} onSelectStop={noop} />
    );
    expect(screen.getByRole("status").textContent).toMatch(/searching/i);

    rerender(
      <ResultsList routeList={EMPTY_LIST} stopList={EMPTY_LIST} state="error" errorDetail="Search cannot load right now." onSelectRoute={noop} onSelectStop={noop} />
    );
    expect(screen.getByRole("alert").textContent).toMatch(/cannot load/);

    rerender(
      <ResultsList routeList={EMPTY_LIST} stopList={EMPTY_LIST} state="no-match" errorDetail="" onSelectRoute={noop} onSelectStop={noop} />
    );
    expect(screen.getByRole("status").textContent).toMatch(/nothing matched/i);

    rerender(
      <ResultsList routeList={EMPTY_LIST} stopList={EMPTY_LIST} state="empty" errorDetail="" onSelectRoute={noop} onSelectStop={noop} />
    );
    expect(screen.getByRole("status").textContent).toMatch(/no routes or stops/i);
  });

  it("lists matching routes and stops with plain fallbacks, wiring picks", () => {
    const onSelectRoute = vi.fn();
    const onSelectStop = vi.fn();
    render(
      <ResultsList routeList={ROUTE_LIST} stopList={STOP_LIST} state="ok" errorDetail="" onSelectRoute={onSelectRoute} onSelectStop={onSelectStop} />
    );
    fireEvent.click(screen.getByRole("button", { name: /Ernakulam — Fort Kochi/ }));
    expect(onSelectRoute).toHaveBeenCalledWith(17);
    // Null names fall back to origin — destination, never a blank label.
    fireEvent.click(screen.getByRole("button", { name: /Aluva — Angamaly/ }));
    expect(onSelectRoute).toHaveBeenCalledWith(18);
    // Stops live under their own tab; routes stay hidden there and back.
    expect(screen.queryByRole("button", { name: /Ernakulam South/ })).toBeNull();
    fireEvent.click(screen.getByRole("tab", { name: "Stops" }));
    fireEvent.click(screen.getByRole("button", { name: /Ernakulam South/ }));
    expect(onSelectStop).toHaveBeenCalledWith(STOPS[0]);
    fireEvent.click(screen.getByRole("tab", { name: "Routes" }));
    expect(screen.queryByRole("button", { name: /Ernakulam South/ })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: /Ernakulam — Fort Kochi/ }));
    expect(onSelectRoute).toHaveBeenCalledWith(17);
  });

  it("groups each route's details inside its own card", () => {
    const noop = () => {};
    render(
      <ResultsList routeList={ROUTE_LIST} stopList={STOP_LIST} state="ok" errorDetail="" onSelectRoute={noop} onSelectStop={noop} />
    );
    const card = screen.getByRole("button", { name: /KSRTC/ });
    expect(card.textContent).toMatch(/Ernakulam — Fort Kochi/);
    expect(card.textContent).toMatch(/KSRTC/);
    expect(card.textContent).toMatch(/Ernakulam → Fort Kochi/);
  });

  it("opens directly on the only side that has results", () => {
    const noop = () => {};
    const { rerender } = render(
      <ResultsList routeList={EMPTY_LIST} stopList={STOP_LIST} state="ok" errorDetail="" onSelectRoute={noop} onSelectStop={noop} />
    );
    expect(screen.getByRole("tab", { name: "Stops" }).getAttribute("aria-selected")).toBe("true");
    expect(screen.getByRole("button", { name: /Ernakulam South/ })).toBeTruthy();
    rerender(
      <ResultsList routeList={ROUTE_LIST} stopList={EMPTY_LIST} state="ok" errorDetail="" onSelectRoute={noop} onSelectStop={noop} />
    );
    expect(screen.getByRole("tab", { name: "Routes" }).getAttribute("aria-selected")).toBe("true");
  });

  it("groups same-named stops with inline expand and member pick", () => {
    const onSelectStop = vi.fn();
    const dupes = [
      { id: 201, name: "Aluva", name_ml: null, lat: 10.11, lon: 76.35 },
      { id: 202, name: "Aluva", name_ml: null, lat: 10.12, lon: 76.36 },
      { id: 203, name: "Aluva", name_ml: null, lat: 10.13, lon: 76.37 },
      { id: 204, name: "Angamaly", name_ml: null, lat: 10.2, lon: 76.4 },
    ];
    render(
      <ResultsList
        routeList={EMPTY_LIST}
        stopList={{ items: dupes, page: 1, totalPages: 1, count: 4 }}
        state="ok"
        errorDetail=""
        onSelectRoute={() => {}}
        onSelectStop={onSelectStop}
      />
    );
    // Auto-switched to the stops tab; one grouped row, members hidden.
    const group = screen.getByRole("button", { name: /Aluva.*3 stops/ });
    expect(group.getAttribute("aria-expanded")).toBe("false");
    expect(screen.queryAllByRole("button", { name: "Aluva" })).toHaveLength(0);
    // Single stops render directly, never grouped.
    expect(screen.getByRole("button", { name: "Angamaly" })).toBeTruthy();
    // Expand, pick the middle member, collapse again.
    fireEvent.click(group);
    expect(group.getAttribute("aria-expanded")).toBe("true");
    const members = screen.getAllByRole("button", { name: "Aluva" });
    expect(members).toHaveLength(3);
    fireEvent.click(members[1]);
    expect(onSelectStop).toHaveBeenCalledWith(dupes[1]);
    fireEvent.click(screen.getByRole("button", { name: /Aluva.*3 stops/ }));
    expect(screen.queryAllByRole("button", { name: "Aluva" })).toHaveLength(0);
  });

  it("shows page info with independent prev/next per tab", () => {
    const onRoutePage = vi.fn();
    const onStopPage = vi.fn();
    render(
      <ResultsList
        routeList={{ items: ROUTES, page: 2, totalPages: 5, count: 97 }}
        stopList={{ items: STOPS, page: 1, totalPages: 1, count: 1 }}
        state="ok"
        errorDetail=""
        onSelectRoute={() => {}}
        onSelectStop={() => {}}
        onRoutePage={onRoutePage}
        onStopPage={onStopPage}
      />
    );
    expect(screen.getByText("Page 2 of 5 · 97 routes")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Next routes page/ }));
    expect(onRoutePage).toHaveBeenCalledWith(3);
    fireEvent.click(screen.getByRole("button", { name: /Previous routes page/ }));
    expect(onRoutePage).toHaveBeenCalledWith(1);
    fireEvent.click(screen.getByRole("tab", { name: "Stops" }));
    expect(screen.getByText("Page 1 of 1 · 1 stops")).toBeTruthy();
    expect(screen.getByRole("button", { name: /Previous stops page/ }).disabled).toBe(true);
    expect(screen.getByRole("button", { name: /Next stops page/ }).disabled).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: /Next stops page/ }));
    expect(onStopPage).not.toHaveBeenCalled();
  });
});
