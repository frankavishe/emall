import type { DeliveryLeg, OrderTotals } from "@/lib/api-client";
import { formatCurrency } from "@/lib/currency";
import { cn } from "@/lib/cn";

/** Items subtotal, one delivery line per shop (with its distance), and the total. Used by the
 * checkout quote and by order detail pages. */
export function DeliverySummary({
  totals,
  legs,
  pending = false,
}: {
  totals: OrderTotals;
  legs: DeliveryLeg[];
  /** Dim the figures while a fresher quote is loading. */
  pending?: boolean;
}) {
  return (
    <dl className={cn("flex flex-col gap-1.5 text-sm", pending && "opacity-60")}>
      <Row label="Items" value={formatCurrency(totals.items_subtotal)} />
      {legs.length > 0 ? (
        legs.map((leg) => (
          <Row
            key={leg.shop_id}
            label={`Delivery from ${leg.shop_name} (${Number(leg.distance_km).toFixed(1)} km)`}
            value={formatCurrency(leg.fee)}
            muted
          />
        ))
      ) : (
        <Row label="Delivery" value={formatCurrency(totals.delivery_fee)} muted />
      )}
      <div className="mt-1 border-t border-border pt-2">
        <Row label="Total" value={formatCurrency(totals.total)} strong />
      </div>
    </dl>
  );
}

function Row({
  label,
  value,
  muted,
  strong,
}: {
  label: string;
  value: string;
  muted?: boolean;
  strong?: boolean;
}) {
  return (
    <div className="flex items-baseline justify-between gap-4">
      <dt
        className={cn(muted ? "text-text-muted" : "text-text-primary", strong && "font-semibold")}
      >
        {label}
      </dt>
      <dd className={cn("text-text-primary tabular-nums", strong && "font-semibold")}>{value}</dd>
    </div>
  );
}
