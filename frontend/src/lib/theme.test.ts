import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useTheme } from "./theme";
import { THEME_STORAGE_KEY, themeInitScript } from "./theme-script";

function runInitScript(prefersDark: boolean) {
  vi.stubGlobal("matchMedia", (query: string) => ({ matches: prefersDark, media: query }));
  new Function(themeInitScript)();
}

afterEach(() => {
  vi.unstubAllGlobals();
  window.localStorage.clear();
  document.documentElement.removeAttribute("data-theme");
});

describe("themeInitScript", () => {
  it("falls back to the OS preference when nothing is saved", () => {
    runInitScript(true);
    expect(document.documentElement.dataset.theme).toBe("dark");
    runInitScript(false);
    expect(document.documentElement.dataset.theme).toBe("light");
  });

  it("prefers the saved choice over the OS preference", () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "light");
    runInitScript(true);
    expect(document.documentElement.dataset.theme).toBe("light");
  });

  it("ignores an unrecognised saved value", () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "sepia");
    runInitScript(true);
    expect(document.documentElement.dataset.theme).toBe("dark");
  });
});

describe("useTheme", () => {
  it("reads the current theme and toggles it, persisting the choice", async () => {
    document.documentElement.dataset.theme = "dark";
    const { result } = renderHook(() => useTheme());
    expect(result.current.theme).toBe("dark");

    // The MutationObserver notifies asynchronously.
    await act(async () => result.current.toggleTheme());
    expect(document.documentElement.dataset.theme).toBe("light");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("light");
    expect(result.current.theme).toBe("light");
  });
});
