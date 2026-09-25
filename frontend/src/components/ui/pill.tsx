import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export type PillTone =
  | "pending"
  | "processing"
  | "shipped"
  | "delivered"
  | "cancelled"
  | "approved"
  | "rejected"
  | "neutral";

const TONE_CLASSES: Record<PillTone, string> = {
  pending: "bg-status-pending/15 text-status-pending",
  processing: "bg-status-processing/15 text-status-processing",
  shipped: "bg-status-shipped/15 text-navy-900",
  delivered: "bg-status-delivered/15 text-status-delivered",
  cancelled: "bg-status-cancelled/15 text-status-cancelled",
  approved: "bg-status-approved/15 text-status-approved",
  rejected: "bg-status-rejected/15 text-status-rejected",
  neutral: "bg-card-muted text-text-muted",
};

export function statusToTone(status: string): PillTone {
  const normalized = status.toLowerCase();
  if (normalized in TONE_CLASSES) return normalized as PillTone;
  return "neutral";
}

export function Pill({ tone = "neutral", children }: { tone?: PillTone; children: ReactNode }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-pill px-3 py-1 text-xs font-medium",
        TONE_CLASSES[tone],
      )}
    >
      {children}
    </span>
  );
}
