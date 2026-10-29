import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ChatDock from "./ChatDock.jsx";

describe("ChatDock", () => {
  beforeEach(() => {
    const fetch = vi.fn(async () => {
      throw new Error("must not be called");
    });
    vi.stubGlobal("fetch", fetch);
    localStorage.clear();
  });

  it("is labelled coming soon and stays inert on activation", () => {
    render(<ChatDock />);
    expect(screen.getByRole("heading", { name: /journey helper/i })).toBeTruthy();
    expect(screen.getByText(/coming soon/i)).toBeTruthy();
    // No input is collected: there is no text field to type into.
    expect(screen.queryByRole("textbox")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: /ask the journey helper/i }));
    fireEvent.click(screen.getByRole("button", { name: /ask the journey helper/i }));

    expect(screen.getByRole("status").textContent).toMatch(/not available yet/i);
    expect(globalThis.fetch).not.toHaveBeenCalled();
    expect(localStorage.length).toBe(0);
    vi.unstubAllGlobals();
  });
});
