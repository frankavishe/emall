import type { PillTone } from "@/components/ui/pill";

/** "10.00" -> "10%", "12.50" -> "12.5%". */
export function formatRate(rate: string | number | null | undefined): string {
  if (rate === null || rate === undefined || rate === "") return "";
  const value = typeof rate === "string" ? Number(rate) : rate;
  if (Number.isNaN(value)) return "";
  return `${Number(value.toFixed(2))}%`;
}

const PAYOUT_TONES: Record<string, PillTone> = {
  PENDING: "pending",
  PROCESSING: "processing",
  SUCCEEDED: "delivered",
  FAILED: "cancelled",
};

export function payoutStatusTone(status: string): PillTone {
  return PAYOUT_TONES[status] ?? "neutral";
}

export const PAYOUT_NETWORK_LABELS: Record<string, string> = {
  MPESA: "M-Pesa",
  TIGOPESA: "Tigo Pesa",
  AIRTEL: "Airtel Money",
  HALOPESA: "HaloPesa",
};

/** A valid commission percent string for the API, or null if `input` isn't 0–100. */
export function parseRateInput(input: string): string | null {
  const trimmed = input.trim().replace(/%$/, "");
  if (!/^\d+(\.\d{1,2})?$/.test(trimmed)) return null;
  const value = Number(trimmed);
  return value >= 0 && value <= 100 ? trimmed : null;
}
