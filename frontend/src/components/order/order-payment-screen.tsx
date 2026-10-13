"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  ApiError,
  MOBILE_MONEY_PROVIDERS,
  PAYMENT_SIMULATOR_ENABLED,
  type OrderDetail,
  type PaymentStatus,
} from "@/lib/api-client";
import { formatCurrency } from "@/lib/currency";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ErrorText, LoadingText } from "@/components/ui/status-text";
import type { BackLink } from "@/components/order/order-detail-screen";

const POLL_INTERVAL_MS = 3000;

/** "Check your phone": shown after a mobile-money checkout until AzamPay confirms or fails the
 * payment. Polls the payment status and moves on to the order page (`orderHref`) once it's paid.
 * Shared by customers and guests (guest checkout); nothing is fetched until `enabled`. */
export function OrderPaymentScreen({
  enabled,
  loadOrder,
  loadStatus,
  orderHref,
  back,
}: {
  enabled: boolean;
  loadOrder: () => Promise<OrderDetail>;
  loadStatus: () => Promise<PaymentStatus>;
  orderHref: string;
  back: BackLink;
}) {
  const router = useRouter();
  const [order, setOrder] = useState<OrderDetail | null>(null);
  const [status, setStatus] = useState<PaymentStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    loadOrder()
      .then((result) => {
        if (!cancelled) setOrder(result);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err instanceof ApiError && err.status === 404
              ? "This order doesn't exist."
              : "Something went wrong. Please try again.",
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, [enabled, loadOrder]);

  const isSettled = status !== null && status.order_status !== "AWAITING_PAYMENT";

  useEffect(() => {
    if (!enabled || isSettled) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function poll() {
      try {
        const result = await loadStatus();
        if (cancelled) return;
        setStatus(result);
        if (result.order_status === "PLACED") {
          router.replace(orderHref);
          return;
        }
        if (result.order_status !== "AWAITING_PAYMENT") return;
      } catch {
        // A dropped poll is retried on the next tick.
      }
      if (!cancelled) timer = setTimeout(poll, POLL_INTERVAL_MS);
    }

    void poll();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [enabled, loadStatus, orderHref, router, isSettled]);

  if (!enabled) {
    return (
      <PageShell size="md" className="min-h-screen items-center justify-center">
        <LoadingText />
      </PageShell>
    );
  }

  if (error) {
    return (
      <PageShell size="md" className="min-h-screen items-center justify-center">
        <ErrorText>{error}</ErrorText>
        <Link href={back.href} className="text-sm font-medium text-brand-text underline">
          {back.label}
        </Link>
      </PageShell>
    );
  }

  const providerLabel =
    MOBILE_MONEY_PROVIDERS.find((option) => option.value === order?.payment.provider)?.label ??
    "mobile money";
  const failed = status?.order_status === "PAYMENT_FAILED";

  return (
    <PageShell size="md">
      <Card className="flex flex-col items-center gap-4 text-center">
        {failed ? (
          <>
            <h1 className="text-2xl font-semibold text-text-primary">Payment not completed</h1>
            <ErrorText>{status?.failure_reason || "The payment was not completed."}</ErrorText>
            <p className="text-sm text-text-muted">
              Nothing was charged and your cart is just as you left it.
            </p>
            <div className="flex flex-wrap justify-center gap-2">
              <Button asChild>
                <Link href="/checkout">Try again</Link>
              </Button>
              <Button asChild variant="secondary">
                <Link href="/cart">Back to cart</Link>
              </Button>
            </div>
          </>
        ) : (
          <>
            <div
              aria-hidden
              className="h-10 w-10 animate-spin rounded-full border-4 border-border border-t-navy-900"
            />
            <h1 className="text-2xl font-semibold text-text-primary">Check your phone</h1>
            {order ? (
              <p className="max-w-md text-sm text-text-muted">
                We sent a {providerLabel} payment prompt for{" "}
                <span className="font-medium text-text-primary">{formatCurrency(order.total)}</span>{" "}
                to <span className="font-medium text-text-primary">{order.payment.msisdn}</span>.
                Enter your PIN on your phone to confirm order #{order.id}.
              </p>
            ) : (
              <LoadingText>Loading order…</LoadingText>
            )}
            <p className="text-xs text-text-muted">This page updates by itself.</p>
            {PAYMENT_SIMULATOR_ENABLED && (
              <Link
                href="/dev/azampay-sandbox"
                target="_blank"
                className="text-sm font-medium text-brand-text underline"
              >
                Open the AzamPay sandbox phone (dev)
              </Link>
            )}
          </>
        )}
      </Card>
    </PageShell>
  );
}
