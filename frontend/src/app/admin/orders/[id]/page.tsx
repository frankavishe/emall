"use client";

import { useState, type ReactNode } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ApiError,
  getAdminOrder,
  paymentMethodLabel,
  settleOrderPayment,
  type AdminOrderDetail,
} from "@/lib/api-client";
import { formatCurrency } from "@/lib/currency";
import { formatRate, payoutStatusTone } from "@/lib/finance";
import { useApi, useRequireRole } from "@/lib/use-api";
import { useRealtime } from "@/lib/realtime";
import { PageShell } from "@/components/ui/page-shell";
import { ErrorState } from "@/components/ui/error-state";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FormField, inputClassName } from "@/components/ui/form-field";
import { Pill, statusToTone } from "@/components/ui/pill";
import { ErrorText, LoadingText } from "@/components/ui/status-text";
import { MapLink } from "@/components/map-link";

export default function AdminOrderDetailPage() {
  const params = useParams<{ id: string }>();
  const allowed = useRequireRole("ADMINISTRATOR");
  const order = useApi(() => getAdminOrder(params.id), params.id, allowed);
  // Administrators hear about every order; refetch when it's this one.
  useRealtime(
    (event) => {
      if (
        "order_id" in event &&
        event.order_id === Number(params.id) &&
        event.type !== "delivery.assigned"
      ) {
        order.reload();
      }
    },
    { enabled: allowed },
  );

  if (!allowed || (order.isLoading && !order.data)) {
    return (
      <PageShell size="md" className="min-h-screen items-center justify-center">
        <LoadingText />
      </PageShell>
    );
  }

  const data = order.data;
  if (!data) {
    const isMissing = !order.error || order.errorStatus === 404;
    return (
      <ErrorState
        code={isMissing ? "404" : undefined}
        title={isMissing ? "Order not found" : "Couldn't load this order"}
        description={isMissing ? "It may have been removed, or the link is wrong." : order.error}
        actions={
          <Button asChild>
            <Link href="/admin/orders">Back to orders</Link>
          </Button>
        }
      />
    );
  }

  const vendorTotal = data.items.reduce((sum, line) => sum + Number(line.vendor_earning), 0);

  return (
    <PageShell
      size="md"
      title={`Order #${data.id}`}
      description={`Placed ${new Date(data.placed_at).toLocaleString()}`}
    >
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Card padding="sm" className="flex flex-col gap-1 text-sm">
          <h2 className="font-semibold text-text-primary">Customer</h2>
          <p className="text-text-primary">
            {data.customer.name}
            {data.customer.is_guest && <span className="text-text-muted"> (guest)</span>}
          </p>
          <p className="text-text-muted">{data.customer.email}</p>
          <h3 className="mt-2 font-medium text-text-primary">Ship to</h3>
          <p className="text-text-muted">{data.recipient_name}</p>
          <p className="text-text-muted">{data.address_line}</p>
          <p className="text-text-muted">
            {data.city}, {data.region} {data.postal_code}
          </p>
          <p className="text-text-muted">{data.country}</p>
          <p className="text-text-muted">{data.phone}</p>
          <MapLink latitude={data.latitude} longitude={data.longitude}>
            View delivery pin
          </MapLink>
        </Card>

        <Card padding="sm" className="flex flex-col gap-2 text-sm">
          <h2 className="font-semibold text-text-primary">Payment</h2>
          {data.payment ? (
            <>
              <Row label="Paid to the mall">{formatCurrency(data.payment.amount)}</Row>
              <Row label="Method">{paymentMethodLabel(data.payment.method)}</Row>
              <Row label="Status">{data.payment.status}</Row>
              {data.payment.provider_reference && (
                <Row
                  label={
                    data.payment.method === "lipa_namba" ? "Customer's txn ID" : "Provider ref"
                  }
                >
                  <span className="break-all font-mono">{data.payment.provider_reference}</span>
                </Row>
              )}
              <Row label="Reference">
                <span className="break-all">{data.payment.transaction_reference}</span>
              </Row>
              {data.payment.failure_reason && (
                <Row label="Reason">{data.payment.failure_reason}</Row>
              )}
              {data.payment.settled_by && (
                <Row label="Settled by">
                  {data.payment.settled_by}
                  {data.payment.settled_at &&
                    ` · ${new Date(data.payment.settled_at).toLocaleString()}`}
                </Row>
              )}
              <ManualPaymentActions order={data} onSettled={order.reload} />
            </>
          ) : (
            <p className="text-text-muted">No payment record.</p>
          )}
          <hr className="border-border" />
          <Row label="Items">{formatCurrency(data.items_subtotal)}</Row>
          {data.deliveries.map((leg) => (
            <Row
              key={leg.shop_id}
              label={`Delivery from ${leg.shop_name} (${Number(leg.distance_km).toFixed(1)} km)`}
            >
              {formatCurrency(leg.fee)}
            </Row>
          ))}
          <Row label="Delivery fee (mall revenue)">{formatCurrency(data.delivery_fee)}</Row>
          <Row label="Order total">{formatCurrency(data.total)}</Row>
          <hr className="border-border" />
          <Row label="Mall commission">{formatCurrency(data.commission_total)}</Row>
          <Row label="Owed to shops">{formatCurrency(vendorTotal)}</Row>
        </Card>
      </div>

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold text-text-primary">Lines</h2>
        <ul className="flex flex-col gap-2">
          {data.items.map((line) => (
            <Card as="li" key={line.id} padding="sm" className="flex flex-col gap-2 text-sm">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <p className="font-medium text-text-primary">{line.product_name}</p>
                  <p className="text-text-muted">
                    <Link href={`/admin/shops/${line.shop.id}`} className="underline">
                      {line.shop.name}
                    </Link>{" "}
                    &middot; {line.quantity} &times; {formatCurrency(line.unit_price)} ={" "}
                    {formatCurrency(line.subtotal)}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Pill tone={statusToTone(line.status)}>{line.status}</Pill>
                  {line.payout && (
                    <Link href={`/admin/payouts/${line.payout.id}`}>
                      <Pill tone={payoutStatusTone(line.payout.status)}>
                        Payout {line.payout.status}
                      </Pill>
                    </Link>
                  )}
                </div>
              </div>
              <p className="text-text-muted">
                Commission {formatRate(line.commission_rate)}:{" "}
                {formatCurrency(line.commission_amount)} &middot; Shop gets{" "}
                <span className="font-medium text-text-primary">
                  {formatCurrency(line.vendor_earning)}
                </span>
              </p>
            </Card>
          ))}
        </ul>
      </section>
    </PageShell>
  );
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-wrap justify-between gap-2">
      <span className="text-text-muted">{label}</span>
      <span className="text-text-primary">{children}</span>
    </div>
  );
}

const MANUAL_METHODS = ["cod", "lipa_namba"];

/** Confirm or reject a cash-on-delivery / Lipa Namba payment that is still pending. */
function ManualPaymentActions({
  order,
  onSettled,
}: {
  order: AdminOrderDetail;
  onSettled: () => void;
}) {
  const [mode, setMode] = useState<"idle" | "confirm" | "reject">("idle");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const payment = order.payment;

  if (!payment || !MANUAL_METHODS.includes(payment.method) || payment.status !== "PENDING") {
    return null;
  }

  const isCod = payment.method === "cod";

  async function settle(action: "confirm" | "reject") {
    setIsSaving(true);
    setError(null);
    try {
      await settleOrderPayment(order.id, action, action === "reject" ? reason.trim() : "");
      setMode("idle");
      onSettled();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't save. Please try again.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="mt-2 flex flex-col gap-2 border-t border-border pt-3">
      {mode === "idle" && (
        <>
          <p className="text-text-muted">
            {isCod
              ? "Confirm once the rider has handed over the cash."
              : "Check this transaction ID and amount on the till statement before confirming."}
          </p>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" onClick={() => setMode("confirm")}>
              {isCod ? "Cash received" : "Confirm payment"}
            </Button>
            <Button size="sm" variant="secondary" onClick={() => setMode("reject")}>
              {isCod ? "Not paid" : "Reject"}
            </Button>
          </div>
        </>
      )}

      {mode === "confirm" && (
        <>
          <p className="text-text-primary">
            Mark {formatCurrency(payment.amount)} as received for order #{order.id}?
            {!isCod && " The order will be released to the shops."}
          </p>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" disabled={isSaving} onClick={() => settle("confirm")}>
              {isSaving ? "Saving…" : "Yes, received"}
            </Button>
            <Button size="sm" variant="ghost" disabled={isSaving} onClick={() => setMode("idle")}>
              Cancel
            </Button>
          </div>
        </>
      )}

      {mode === "reject" && (
        <>
          <p className="text-text-primary">
            This cancels every line of the order and returns its stock.
          </p>
          <FormField label="Reason (shown to the customer)">
            <input
              type="text"
              maxLength={255}
              value={reason}
              placeholder={isCod ? "Customer refused to pay" : "No matching transaction found"}
              onChange={(e) => setReason(e.target.value)}
              className={inputClassName}
            />
          </FormField>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="danger" disabled={isSaving} onClick={() => settle("reject")}>
              {isSaving ? "Saving…" : "Reject payment"}
            </Button>
            <Button size="sm" variant="ghost" disabled={isSaving} onClick={() => setMode("idle")}>
              Cancel
            </Button>
          </div>
        </>
      )}

      {error && <ErrorText>{error}</ErrorText>}
    </div>
  );
}
