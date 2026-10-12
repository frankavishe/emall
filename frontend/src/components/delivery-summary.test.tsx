import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { DeliverySummary } from "./delivery-summary";
import { formatCurrency } from "@/lib/currency";

afterEach(cleanup);

// Testing Library collapses the formatter's non-breaking space to a plain space.
const money = (value: string) => formatCurrency(value).replace(/\s/g, " ");

const TOTALS = { items_subtotal: "14000.00", delivery_fee: "7200.00", total: "21200.00" };

describe("DeliverySummary", () => {
  it("shows one delivery line per shop with its distance, and the total", () => {
    render(
      <DeliverySummary
        totals={TOTALS}
        legs={[
          { shop_id: 1, shop_name: "Kariakoo Traders", distance_km: "0.00", fee: "2000.00" },
          { shop_id: 2, shop_name: "Mlimani Books", distance_km: "4.82", fee: "5200.00" },
        ]}
      />,
    );

    expect(screen.getByText("Delivery from Kariakoo Traders (0.0 km)")).toBeTruthy();
    expect(screen.getByText("Delivery from Mlimani Books (4.8 km)")).toBeTruthy();
    expect(screen.getByText(money("5200.00"))).toBeTruthy();
    expect(screen.getByText("Total")).toBeTruthy();
    expect(screen.getByText(money("21200.00"))).toBeTruthy();
  });

  it("falls back to a single delivery line when there are no legs (older orders)", () => {
    render(
      <DeliverySummary
        totals={{ items_subtotal: "200.00", delivery_fee: "0.00", total: "200.00" }}
        legs={[]}
      />,
    );

    expect(screen.getByText("Delivery")).toBeTruthy();
    expect(screen.getByText(money("0.00"))).toBeTruthy();
  });
});
