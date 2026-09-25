import type { ReactNode } from "react";

export const inputClassName =
  "rounded-control border border-border bg-card px-3 py-2 text-sm text-text-primary outline-none transition-colors focus:border-navy-900/40 focus:ring-2 focus:ring-navy-900/10";

export function FormField({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="flex flex-col gap-1 text-sm font-medium text-text-primary">
      {label}
      {children}
    </label>
  );
}
