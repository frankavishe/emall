"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ApiError,
  MOBILE_MONEY_PROVIDERS,
  paymentMethodLabel,
  type OrderDetail,
} from "@/lib/api-client";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Pill, statusToTone } from "@/components/ui/pill";
import { ErrorText, LoadingText } from "@/components/ui/status-text";
import { formatCurrency } from "@/lib/currency";
import { DeliverySummary } from "@/components/delivery-summary";
import { MapLink } from "@/components/map-link";

export type BackLink = { href: string; label: string };

/** An order's detail, shared by a customer's `/orders/{id}` and a guest's
 * `/orders/track/{token}` (guest checkout). `orderHref` is the order's own path, `/pay` hangs off
 * it. Nothing is fetched until `enabled`, so callers can wait for their auth check. */
export function OrderDetailScreen({
  enabled,
  load,
  orderHref,
  back,
  notice,
}: {
  enabled: boolean;
  load: () => Promise<OrderDetail>;
  orderHref: string;
  back: BackLink;
  notice?: React.ReactNode;
}) {
  const [order, setOrder] = useState<OrderDetail | null>(null);
  const [isLoadingOrder, setIsLoadingOrder] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;

    async function run() {
      setIsLoadingOrder(true);
      setError(null);
      try {
        const result = await load();
        if (!cancelled) setOrder(result);
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof ApiError && err.status === 404
              ? "This order doesn't exist."
              : "Something went wrong. Please try again.",
          );
        }
      } finally {
        if (!cancelled) setIsLoadingOrder(false);
      }
    }

    void run();
    return () => {
      cancelled = true;
    };
  }, [enabled, load]);

  if (!enabled) {
    return (
      <PageShell size="md" className="min-h-screen items-center justify-center">
        <LoadingText />
      </PageShell>
    );
  }

  if (isLoadingOrder) {
    return (
      <PageShell size="md" className="min-h-screen items-center justify-center">
        <LoadingText>Loading order…</LoadingText>
      </PageShell>
    );
  }

  if (error || !order) {
    return (
      <PageShell size="md" className="min-h-screen items-center justify-center">
        <ErrorText>{error ?? "Order not found."}</ErrorText>
        <Link href={back.href} className="text-sm font-medium text-brand-text underline">
          {back.label}
        </Link>
      </PageShell>
    );
  }

  return (
    <PageShell size="md">
      <Link href={back.href} className="text-sm font-medium text-brand-text underline">
        {back.label}
      </Link>

      {notice}

      <Card className="flex flex-col gap-6">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h1 className="text-2xl font-semibold text-text-primary">Order #{order.id}</h1>
            <p className="mt-1 text-sm text-text-muted">
              Placed {new Date(order.placed_at).toLocaleString()}
            </p>
          </div>
          <Pill tone={statusToTone(order.status)}>{order.status}</Pill>
        </div>

        <div className="grid grid-cols-1 gap-8 md:grid-cols-2">
          <div>
            <h2 className="text-sm font-semibold text-text-muted">Delivery address</h2>
            <p className="mt-2 text-sm text-text-primary">{order.shipping.recipient_name}</p>
            <p className="text-sm text-text-primary">{order.shipping.address_line}</p>
            <p className="text-sm text-text-primary">
              {order.shipping.city}, {order.shipping.region} {order.shipping.postal_code}
            </p>
            <p className="text-sm text-text-primary">{order.shipping.country}</p>
            <p className="text-sm text-text-primary">{order.shipping.phone}</p>
            <MapLink
              latitude={order.shipping.latitude}
              longitude={order.shipping.longitude}
              className="mt-1 inline-block"
            >
              View delivery pin
            </MapLink>
          </div>

          <div>
            <h2 className="text-sm font-semibold text-text-muted">Payment</h2>
            <p className="mt-2 text-sm text-text-primary">
              {paymentMethodLabel(order.payment.method)}
            </p>
            {order.payment.provider && (
              <p className="text-sm text-text-primary">
                {MOBILE_MONEY_PROVIDERS.find((p) => p.value === order.payment.provider)?.label ??
                  order.payment.provider}{" "}
                &middot; {order.payment.msisdn}
              </p>
            )}
            {order.payment.payer_reference && (
              <p className="text-sm text-text-primary">
                Transaction ID <span className="font-mono">{order.payment.payer_reference}</span>
              </p>
            )}
            <p className="text-sm text-text-primary">
              {order.payment.method === "cod" && order.payment.status === "PENDING"
                ? `Pay ${formatCurrency(order.total)} in cash on delivery`
                : order.payment.method === "lipa_namba" && order.payment.status === "PENDING"
                  ? "Awaiting payment verification"
                  : order.payment.status}
            </p>
            {order.payment.failure_reason && (
              <p className="text-sm text-status-cancelled">{order.payment.failure_reason}</p>
            )}
            {order.status === "AWAITING_PAYMENT" && (
              <Link
                href={`${orderHref}/pay`}
                className="text-sm font-medium text-brand-text underline"
              >
                Waiting for your payment — view status
              </Link>
            )}
          </div>
        </div>

        <div>
          <h2 className="mb-2 text-sm font-semibold text-text-muted">Items</h2>
          <ul className="flex flex-col gap-3">
            {order.items.map((item) => (
              <Card as="li" key={item.id} variant="muted" padding="sm">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-medium text-text-primary">{item.product.name}</p>
                    <p className="text-sm text-text-muted">Sold by {item.shop_name}</p>
                    <p className="mt-1 text-sm text-text-muted">
                      {item.quantity} &times; {formatCurrency(item.unit_price)}
                    </p>
                    <Pill tone={statusToTone(item.status)}>{item.status}</Pill>
                    {item.rider && item.status !== "DELIVERED" && item.status !== "CANCELLED" && (
                      <p className="mt-1 text-sm text-text-muted">
                        Your rider: {item.rider.name} &middot;{" "}
                        <a href={`tel:${item.rider.phone}`} className="underline">
                          {item.rider.phone}
                        </a>
                      </p>
                    )}
                  </div>
                  <p className="font-medium text-text-primary">{formatCurrency(item.subtotal)}</p>
                </div>
              </Card>
            ))}
          </ul>
        </div>

        <div className="flex justify-end border-t border-border pt-6">
          <div className="w-full max-w-sm">
            <DeliverySummary totals={order} legs={order.deliveries} />
          </div>
        </div>
      </Card>
    </PageShell>
  );
}
