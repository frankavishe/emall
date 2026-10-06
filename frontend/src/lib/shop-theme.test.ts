import { describe, expect, it } from "vitest";
import { isHexColor, isLightColor, shopThemeStyle } from "./shop-theme";

describe("shopThemeStyle", () => {
  it("returns undefined when the shop has no theme", () => {
    expect(shopThemeStyle(null)).toBeUndefined();
    expect(shopThemeStyle({ primary_color: "", accent_color: "" })).toBeUndefined();
    expect(shopThemeStyle({ primary_color: "not-a-color" })).toBeUndefined();
  });

  it("maps the primary color onto the navy tokens with white text on dark colors", () => {
    const style = shopThemeStyle({ primary_color: "#7a1f1f", accent_color: "" }) as Record<
      string,
      string
    >;
    expect(style["--color-navy-900"]).toBe("#7a1f1f");
    expect(style["--color-navy-800"]).toContain("#7a1f1f");
    expect(style["--color-on-primary"]).toBe("#ffffff");
    expect(style["--color-teal-400"]).toBeUndefined();
  });

  it("flips text to dark on a light primary", () => {
    const style = shopThemeStyle({ primary_color: "#fde047" }) as Record<string, string>;
    expect(style["--color-on-primary"]).toBe("#0f172a");
    expect(style["--color-text-inverse"]).toBe("#0f172a");
  });

  it("maps the accent color onto the teal tokens", () => {
    const style = shopThemeStyle({ accent_color: "#ff8800" }) as Record<string, string>;
    expect(style["--color-teal-400"]).toBe("#ff8800");
    expect(style["--color-teal-100"]).toContain("#ff8800");
    expect(style["--color-navy-900"]).toBeUndefined();
  });
});

describe("color helpers", () => {
  it("validates #rrggbb", () => {
    expect(isHexColor("#a1B2c3")).toBe(true);
    expect(isHexColor("#abc")).toBe(false);
    expect(isHexColor("")).toBe(false);
  });

  it("classifies light and dark colors", () => {
    expect(isLightColor("#ffffff")).toBe(true);
    expect(isLightColor("#0f2a4a")).toBe(false);
  });
});
