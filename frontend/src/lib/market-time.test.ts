import { describe, expect, it } from "vitest";
import { addMarketDays, formatMarketDate, formatMarketTime, marketToday } from "./market-time";

describe("market time", () => {
  it("shows Dar es Salaam time whatever offset the timestamp carries", () => {
    expect(formatMarketTime("2026-11-20T09:00:00+03:00")).toBe("09:00");
    expect(formatMarketTime("2026-11-20T06:00:00Z")).toBe("09:00");
    expect(formatMarketTime("2026-11-20T01:00:00-05:00")).toBe("09:00");
  });

  it("uses the market date around midnight", () => {
    // 22:30 UTC on the 19th is already 01:30 on the 20th in Dar es Salaam.
    expect(marketToday(new Date("2026-11-19T22:30:00Z"))).toBe("2026-11-20");
    expect(marketToday(new Date("2026-11-19T20:30:00Z"))).toBe("2026-11-19");
    expect(formatMarketDate("2026-11-19T22:30:00Z")).toBe(formatMarketDate("2026-11-20"));
  });

  it("formats a plain date without shifting it", () => {
    expect(formatMarketDate("2026-11-20")).toContain("20 Nov 2026");
  });

  it("adds days across month and year ends", () => {
    expect(addMarketDays("2026-11-30", 1)).toBe("2026-12-01");
    expect(addMarketDays("2026-12-31", 60)).toBe("2027-03-01");
  });
});
