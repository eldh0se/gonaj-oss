import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import RouteOverlay from "./RouteOverlay.jsx";

const DETAIL = {
  id: 17,
  name: "Ernakulam — Fort Kochi",
  origin: "Ernakulam",
  destination: "Fort Kochi",
  operator: "KSRTC",
  network: null,
  stops: [
    { stop: { id: 1, name: "Ernakulam South", lat: 9.97, lon: 76.28 }, position: 1, is_origin: true, is_terminus: false },
    { stop: { id: 2, name: "Marine Drive", lat: 9.975, lon: 76.28 }, position: 2, is_origin: false, is_terminus: false },
    { stop: { id: 3, name: "Fort Kochi", lat: 9.96, lon: 76.24 }, position: 3, is_origin: false, is_terminus: true },
  ],
};

describe("RouteOverlay", () => {
  it("shows ordered stops with origin and terminus marked", () => {
    const noop = () => {};
    render(<RouteOverlay detail={DETAIL} state="ok" errorDetail="" onDismiss={noop} />);
    expect(screen.getByRole("heading", { name: /Ernakulam — Fort Kochi/ })).toBeTruthy();
    const items = screen.getAllByRole("listitem").map((li) => li.textContent);
    expect(items[0]).toMatch(/Ernakulam South/);
    expect(items[0]).toMatch(/origin/);
    expect(items[2]).toMatch(/Fort Kochi/);
    expect(items[2]).toMatch(/terminus/);
    expect(items[1]).not.toMatch(/origin|terminus/);
    expect(screen.getByRole("button", { name: /close/i })).toBeTruthy();
  });

  it("states empty membership plainly and dismisses", () => {
    const onDismiss = vi.fn();
    render(
      <RouteOverlay detail={{ ...DETAIL, stops: [] }} state="empty" errorDetail="" onDismiss={onDismiss} />
    );
    expect(screen.getByRole("status").textContent).toMatch(/no stops are recorded/i);
    fireEvent.click(screen.getByRole("button", { name: /close/i }));
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it("reports unknown routes and failures in plain language", () => {
    const noop = () => {};
    const { rerender } = render(
      <RouteOverlay detail={null} state="not-found" errorDetail="" onDismiss={noop} />
    );
    expect(screen.getByRole("alert").textContent).toMatch(/could not find that route/);
    rerender(
      <RouteOverlay detail={null} state="error" errorDetail="That route cannot load right now." onDismiss={noop} />
    );
    expect(screen.getByRole("alert").textContent).toMatch(/cannot load/);
    rerender(
      <RouteOverlay detail={null} state="loading" errorDetail="" onDismiss={noop} />
    );
    expect(screen.getByRole("status").textContent).toMatch(/loading route/i);
  });
});
