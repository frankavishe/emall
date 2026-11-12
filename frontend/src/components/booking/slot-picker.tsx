"use client";

import { useState } from "react";
import { getServiceSlots, type ServiceSlot } from "@/lib/api-client";
import {
  addMarketDays,
  formatMarketDate,
  formatMarketTime,
  MARKET_TIME_LABEL,
  marketToday,
} from "@/lib/market-time";
import { useApi } from "@/lib/use-api";
import { cn } from "@/lib/cn";
import { FormField, inputClassName } from "@/components/ui/form-field";
import { EmptyText, ErrorText, LoadingText } from "@/components/ui/status-text";

// The API refuses dates further ahead than this (BOOKING_MAX_ADVANCE_DAYS).
const BOOKING_WINDOW_DAYS = 60;

/**
 * A date picker and the service's open times on that date, always in Dar es Salaam time. Without
 * `onSelect` the times are plain labels. Change `refreshKey` to fetch the times again.
 */
export function SlotPicker({
  serviceId,
  selected = null,
  onSelect,
  refreshKey = 0,
}: {
  serviceId: number;
  selected?: ServiceSlot | null;
  onSelect?: (slot: ServiceSlot | null) => void;
  refreshKey?: number;
}) {
  const today = marketToday();
  const [date, setDate] = useState(today);
  const slots = useApi(
    () => getServiceSlots(serviceId, date),
    `${serviceId}|${date}|${refreshKey}`,
    !!date,
  );

  return (
    <div className="flex flex-col gap-4">
      <FormField label="Date">
        <input
          type="date"
          value={date}
          min={today}
          max={addMarketDays(today, BOOKING_WINDOW_DAYS)}
          onChange={(e) => {
            setDate(e.target.value);
            onSelect?.(null);
          }}
          className={inputClassName}
        />
      </FormField>

      {slots.error ? (
        <ErrorText>{slots.error}</ErrorText>
      ) : slots.isLoading ? (
        <LoadingText>Checking open times…</LoadingText>
      ) : !slots.data || slots.data.slots.length === 0 ? (
        <EmptyText>No open times on {date ? formatMarketDate(date) : "this date"}.</EmptyText>
      ) : (
        <div className="flex flex-col gap-2">
          <p className="text-sm text-text-muted">
            Open times on {formatMarketDate(date)}, in {MARKET_TIME_LABEL}
          </p>
          <ul className="flex flex-wrap gap-2">
            {slots.data.slots.map((slot) =>
              onSelect ? (
                <li key={slot.starts_at}>
                  <button
                    type="button"
                    aria-pressed={selected?.starts_at === slot.starts_at}
                    onClick={() => onSelect(slot)}
                    className={cn(
                      "rounded-pill px-3 py-1.5 text-sm font-medium transition-colors",
                      selected?.starts_at === slot.starts_at
                        ? "bg-navy-900 text-on-primary"
                        : "bg-hover text-text-primary hover:bg-card-muted",
                    )}
                  >
                    {formatMarketTime(slot.starts_at)}
                  </button>
                </li>
              ) : (
                <li
                  key={slot.starts_at}
                  className="rounded-pill bg-hover px-3 py-1.5 text-sm font-medium text-text-primary"
                >
                  {formatMarketTime(slot.starts_at)}
                </li>
              ),
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
