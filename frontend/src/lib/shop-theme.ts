import type { CSSProperties } from "react";

/** A shop's chosen colors — `#rrggbb`, or `""` for the MangiMall default. */
export type ShopTheme = {
  primary_color?: string | null;
  accent_color?: string | null;
};

const HEX_COLOR = /^#[0-9a-f]{6}$/i;
const DARK_TEXT = "#0f172a";
const LIGHT_TEXT = "#ffffff";

export function isHexColor(value: string | null | undefined): value is string {
  return !!value && HEX_COLOR.test(value);
}

/** WCAG relative luminance of a `#rrggbb` color, 0 (black) to 1 (white). */
export function relativeLuminance(hex: string): number {
  const channels = [1, 3, 5].map((start) => {
    const value = parseInt(hex.slice(start, start + 2), 16) / 255;
    return value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
}

/** Whether dark text reads better than white on this background — 0.179 is the luminance at
 * which white and near-black give the same contrast ratio. */
export function isLightColor(hex: string): boolean {
  return relativeLuminance(hex) > 0.179;
}

/** Inline style that re-points the brand tokens (globals.css) at a shop's colors, so every
 * `bg-navy-900` / `text-teal-400` / primary `Button` inside the wrapper takes the shop's theme.
 * Returns `undefined` for a shop with no theme, leaving the MangiMall defaults in place. */
export function shopThemeStyle(theme: ShopTheme | null | undefined): CSSProperties | undefined {
  if (!theme) return undefined;
  const style: Record<string, string> = {};

  const primary = theme.primary_color;
  if (isHexColor(primary)) {
    const onPrimary = isLightColor(primary) ? DARK_TEXT : LIGHT_TEXT;
    style["--color-navy-900"] = primary;
    style["--color-navy-800"] = `color-mix(in srgb, ${primary} 85%, black)`;
    style["--color-navy-700"] = `color-mix(in srgb, ${primary} 80%, white)`;
    style["--color-on-primary"] = onPrimary;
    style["--color-text-inverse"] = onPrimary;
  }

  const accent = theme.accent_color;
  if (isHexColor(accent)) {
    style["--color-teal-400"] = accent;
    style["--color-teal-300"] = `color-mix(in srgb, ${accent} 75%, white)`;
    style["--color-teal-100"] = `color-mix(in srgb, ${accent} 25%, white)`;
  }

  return Object.keys(style).length > 0 ? (style as CSSProperties) : undefined;
}
