"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { FormField, inputClassName } from "@/components/ui/form-field";
import { ErrorText } from "@/components/ui/status-text";
import { ShopLogo } from "@/components/shop-logo";
import { errorMessage, updateShopTheme } from "@/lib/api-client";
import { useAuth, type Shop } from "@/lib/auth-context";
import { cn } from "@/lib/cn";
import { isHexColor, isLightColor, shopThemeStyle } from "@/lib/shop-theme";

// The MangiMall brand colors (globals.css) — what an unthemed shop uses.
const DEFAULT_PRIMARY = "#0f2a4a";
const DEFAULT_ACCENT = "#2dd4bf";

const PRESETS = [
  { name: "MangiMall", primary: DEFAULT_PRIMARY, accent: DEFAULT_ACCENT },
  { name: "Forest", primary: "#14532d", accent: "#a3e635" },
  { name: "Sunset", primary: "#9a3412", accent: "#fbbf24" },
  { name: "Berry", primary: "#701a75", accent: "#f472b6" },
  { name: "Ocean", primary: "#1e3a8a", accent: "#38bdf8" },
  { name: "Charcoal", primary: "#1f2937", accent: "#f87171" },
] as const;

/** Pick a shop's primary and accent colors, with a live preview. Saves on demand, then refreshes
 * the profile so `user.shops` carries the new theme. */
export function ShopThemePicker({ shop }: { shop: Shop }) {
  const { refreshUser } = useAuth();
  const [primary, setPrimary] = useState(shop.primary_color || DEFAULT_PRIMARY);
  const [accent, setAccent] = useState(shop.accent_color || DEFAULT_ACCENT);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const isValid = isHexColor(primary) && isHexColor(accent);
  const isCustom = !!(shop.primary_color || shop.accent_color);
  const isDirty =
    primary.toLowerCase() !== (shop.primary_color || DEFAULT_PRIMARY) ||
    accent.toLowerCase() !== (shop.accent_color || DEFAULT_ACCENT);

  async function save(theme: { primary_color: string; accent_color: string }) {
    setError(null);
    setIsSaving(true);
    try {
      await updateShopTheme(shop.id, theme);
      await refreshUser();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setIsSaving(false);
    }
  }

  function reset() {
    setPrimary(DEFAULT_PRIMARY);
    setAccent(DEFAULT_ACCENT);
    void save({ primary_color: "", accent_color: "" });
  }

  return (
    <div className="flex flex-col gap-3">
      <span className="text-sm font-medium text-text-primary">Shop colors</span>

      <div className="flex flex-wrap gap-2">
        {PRESETS.map((preset) => (
          <button
            key={preset.name}
            type="button"
            onClick={() => {
              setPrimary(preset.primary);
              setAccent(preset.accent);
            }}
            className={cn(
              "flex items-center gap-1.5 rounded-pill border border-border px-2.5 py-1 text-xs text-text-muted hover:bg-card-muted",
              primary === preset.primary && accent === preset.accent && "border-text-primary/40",
            )}
          >
            <span className="h-3 w-3 rounded-full" style={{ background: preset.primary }} />
            <span className="h-3 w-3 rounded-full" style={{ background: preset.accent }} />
            {preset.name}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <ColorField label="Primary" value={primary} onChange={setPrimary} />
        <ColorField label="Accent" value={accent} onChange={setAccent} />
      </div>

      {isValid && (
        <div
          style={shopThemeStyle({ primary_color: primary, accent_color: accent })}
          className="flex items-center gap-3 rounded-control bg-navy-900 p-3"
          aria-label="Theme preview"
        >
          <ShopLogo url={shop.logo_url} name={shop.name} size="sm" />
          <span className="font-semibold text-on-primary">{shop.name}</span>
          <span
            className="ml-auto rounded-pill bg-teal-400 px-2.5 py-0.5 text-xs font-medium"
            style={{ color: isLightColor(accent) ? "#0f172a" : "#ffffff" }}
          >
            New
          </span>
          <span className="rounded-pill bg-card px-3 py-1 text-xs font-medium text-text-primary">
            Shop now
          </span>
        </div>
      )}

      <div className="flex gap-2">
        <Button
          size="sm"
          disabled={isSaving || !isValid || !isDirty}
          onClick={() => void save({ primary_color: primary, accent_color: accent })}
        >
          {isSaving ? "Saving…" : "Save colors"}
        </Button>
        {isCustom && (
          <Button variant="ghost" size="sm" disabled={isSaving} onClick={reset}>
            Reset to default
          </Button>
        )}
      </div>
      {error && <ErrorText>{error}</ErrorText>}
    </div>
  );
}

function ColorField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <FormField label={label}>
      <div className="flex items-center gap-2">
        <input
          type="color"
          value={isHexColor(value) ? value.toLowerCase() : "#000000"}
          onChange={(event) => onChange(event.target.value)}
          aria-label={`${label} color`}
          className="h-9 w-12 shrink-0 cursor-pointer rounded-control border border-border bg-card p-1"
        />
        <input
          type="text"
          value={value}
          maxLength={7}
          onChange={(event) => onChange(event.target.value.trim())}
          aria-invalid={!isHexColor(value)}
          className={cn(
            inputClassName,
            "w-full font-mono",
            !isHexColor(value) && "border-status-cancelled",
          )}
        />
      </div>
    </FormField>
  );
}
