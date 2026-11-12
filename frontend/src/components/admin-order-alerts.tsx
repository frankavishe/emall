"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { hasAdminPermission, useAuth } from "@/lib/auth-context";
import { getAdminOrder, paymentMethodLabel } from "@/lib/api-client";
import { useRealtime } from "@/lib/realtime";
import { formatCurrency } from "@/lib/currency";

const DISMISS_AFTER_MS = 8_000;
const MAX_VISIBLE = 4;

type OrderAlert = {
  orderId: number;
  customer?: string;
  isGuest?: boolean;
  total?: string;
  itemCount?: number;
  payment?: string;
  awaitingPayment?: boolean;
};

/** Pop-up toasts for administrators when a new order comes in, on any admin page. Mounted once
 * by `AppFrame`, so the desktop rail and the mobile menu don't each raise their own. The socket
 * only says which order is new; the details come from the admin order endpoint, and a toast
 * still shows (with just the number) if that fetch fails. */
export function AdminOrderAlerts() {
  const { activeRole, user } = useAuth();
  const enabled = activeRole === "ADMINISTRATOR" && hasAdminPermission(user, "orders.view");
  const [alerts, setAlerts] = useState<OrderAlert[]>([]);
  const timers = useRef(new Map<number, ReturnType<typeof setTimeout>>());

  const dismiss = useCallback((orderId: number) => {
    const timer = timers.current.get(orderId);
    if (timer) clearTimeout(timer);
    timers.current.delete(orderId);
    setAlerts((prev) => prev.filter((alert) => alert.orderId !== orderId));
  }, []);

  const show = useCallback(
    (alert: OrderAlert) => {
      setAlerts((prev) => {
        const rest = prev.filter((a) => a.orderId !== alert.orderId);
        return [alert, ...rest].slice(0, MAX_VISIBLE);
      });
      const existing = timers.current.get(alert.orderId);
      if (existing) clearTimeout(existing);
      timers.current.set(
        alert.orderId,
        setTimeout(() => dismiss(alert.orderId), DISMISS_AFTER_MS),
      );
    },
    [dismiss],
  );

  useEffect(() => {
    const pending = timers.current;
    return () => pending.forEach((timer) => clearTimeout(timer));
  }, []);

  useRealtime(
    (event) => {
      if (event.type !== "order.created") return;
      const orderId = event.order_id;
      // Ignore a repeat announcement while that order's toast is still up.
      if (timers.current.has(orderId)) return;
      show({ orderId });
      void getAdminOrder(orderId)
        .then((order) => {
          setAlerts((prev) =>
            prev.map((a) =>
              a.orderId === orderId
                ? {
                    orderId,
                    customer: order.customer.name,
                    isGuest: order.customer.is_guest,
                    total: order.total,
                    itemCount: order.items.reduce((sum, line) => sum + line.quantity, 0),
                    payment: order.payment ? paymentMethodLabel(order.payment.method) : undefined,
                    awaitingPayment: order.status !== "PLACED",
                  }
                : a,
            ),
          );
        })
        .catch(() => {
          // Keep the number-only toast.
        });
    },
    { enabled },
  );

  if (!enabled) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-[min(22rem,calc(100vw-2rem))] flex-col gap-2"
    >
      {alerts.map((alert) => (
        <div
          key={alert.orderId}
          className="pointer-events-auto flex gap-3 rounded-control border border-border bg-card p-3 shadow-card"
        >
          <span
            aria-hidden
            className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-pill bg-teal-400 text-navy-900"
          >
            <svg
              viewBox="0 0 20 20"
              fill="none"
              stroke="currentColor"
              strokeWidth={1.8}
              strokeLinecap="round"
              strokeLinejoin="round"
              className="h-4 w-4"
            >
              <path d="M6 3.5h8a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1v-12a1 1 0 0 1 1-1zM8 7.5h4M8 10.5h4M8 13.5h2" />
            </svg>
          </span>
          <div className="min-w-0 flex-1 text-sm">
            <p className="font-semibold text-text-primary">New order #{alert.orderId}</p>
            {alert.customer && (
              <p className="truncate text-text-muted">
                {alert.customer}
                {alert.isGuest && " (guest)"}
              </p>
            )}
            {alert.total && (
              <p className="text-text-muted">
                {alert.itemCount} item{alert.itemCount === 1 ? "" : "s"} &middot;{" "}
                <span className="font-medium text-text-primary">{formatCurrency(alert.total)}</span>
                {alert.payment && ` · ${alert.payment}`}
              </p>
            )}
            {alert.awaitingPayment && (
              <p className="text-xs font-medium text-text-muted">Awaiting payment</p>
            )}
            <Link
              href={`/admin/orders/${alert.orderId}`}
              onClick={() => dismiss(alert.orderId)}
              className="mt-1 inline-block text-sm font-medium text-text-primary underline"
            >
              View order
            </Link>
          </div>
          <button
            type="button"
            onClick={() => dismiss(alert.orderId)}
            aria-label={`Dismiss order #${alert.orderId} alert`}
            className="h-6 w-6 shrink-0 rounded-control text-text-muted transition-colors hover:bg-hover hover:text-text-primary"
          >
            &times;
          </button>
        </div>
      ))}
    </div>
  );
}
