import { describe, expect, it } from "vitest";
import { formatRate, parseRateInput, payoutStatusTone } from "./finance";

describe("formatRate", () => {
  it("drops trailing zeros", () => {
    expect(formatRate("10.00")).toBe("10%");
    expect(formatRate("12.50")).toBe("12.5%");
    expect(formatRate(7.25)).toBe("7.25%");
  });

  it("returns an empty string for missing values", () => {
    expect(formatRate(null)).toBe("");
    expect(formatRate("")).toBe("");
    expect(formatRate("abc")).toBe("");
  });
});

describe("parseRateInput", () => {
  it("accepts 0–100 with up to two decimals and an optional %", () => {
    expect(parseRateInput("10")).toBe("10");
    expect(parseRateInput(" 12.5% ")).toBe("12.5");
    expect(parseRateInput("0")).toBe("0");
    expect(parseRateInput("100")).toBe("100");
  });

  it("rejects anything else", () => {
    expect(parseRateInput("100.01")).toBeNull();
    expect(parseRateInput("-1")).toBeNull();
    expect(parseRateInput("1.234")).toBeNull();
    expect(parseRateInput("ten")).toBeNull();
  });
});

describe("payoutStatusTone", () => {
  it("maps payout statuses to pill tones", () => {
    expect(payoutStatusTone("SUCCEEDED")).toBe("delivered");
    expect(payoutStatusTone("FAILED")).toBe("cancelled");
    expect(payoutStatusTone("WHATEVER")).toBe("neutral");
  });
});
