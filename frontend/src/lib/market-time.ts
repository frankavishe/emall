/** Dates and times for bookings. The mall serves Dar es Salaam, so these always show that city's
 * time, never the time zone of the viewer's device (008-service-bookings FR-010). */

export const MARKET_TIME_ZONE = "Africa/Dar_es_Salaam";
export const MARKET_TIME_LABEL = "Dar es Salaam time";

const DAY_MS = 24 * 60 * 60 * 1000;

const timeFormat = new Intl.DateTimeFormat("en-GB", {
  timeZone: MARKET_TIME_ZONE,
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

const dateFormat = new Intl.DateTimeFormat("en-GB", {
  timeZone: MARKET_TIME_ZONE,
  weekday: "short",
  day: "numeric",
  month: "short",
  year: "numeric",
});

// en-CA formats a date as YYYY-MM-DD, the shape `<input type="date">` and the API use.
const isoDateFormat = new Intl.DateTimeFormat("en-CA", {
  timeZone: MARKET_TIME_ZONE,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

/** `2026-11-20T09:00:00+03:00` -> `09:00`. */
export function formatMarketTime(value: string | Date): string {
  return timeFormat.format(new Date(value));
}

/** A full timestamp or a `YYYY-MM-DD` date -> `Fri, 20 Nov 2026`. */
export function formatMarketDate(value: string | Date): string {
  if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
    // Midday, so the calendar date can't shift whatever the zone conversion does.
    return dateFormat.format(new Date(`${value}T12:00:00+03:00`));
  }
  return dateFormat.format(new Date(value));
}

/** `2026-11-20T09:00:00+03:00` -> `Fri, 20 Nov 2026 at 09:00`. */
export function formatMarketDateTime(value: string | Date): string {
  return `${dateFormat.format(new Date(value))} at ${formatMarketTime(value)}`;
}

/** Today's date in Dar es Salaam, as `YYYY-MM-DD`. */
export function marketToday(now: Date = new Date()): string {
  return isoDateFormat.format(now);
}

/** `date` (`YYYY-MM-DD`) moved by `days`. */
export function addMarketDays(date: string, days: number): string {
  const midday = new Date(`${date}T12:00:00+03:00`).getTime();
  return isoDateFormat.format(new Date(midday + days * DAY_MS));
}
