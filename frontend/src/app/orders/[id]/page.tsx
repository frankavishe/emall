"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { ApiError, getOrder, type OrderDetail } from "@/lib/api-client";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Pill, statusToTone } from "@/components/ui/pill";
import { ErrorText, LoadingText } from "@/components/ui/status-text";

export default function OrderDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { user, isLoading } = useAuth();
  const [order, setOrder] = useState<OrderDetail | null>(null);
  const [isLoadingOrder, setIsLoadingOrder] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoading && (!user || user.role !== "CUSTOMER")) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  useEffect(() => {
    if (user?.role !== "CUSTOMER") return;
    let cancelled = false;

    async function run() {
      setIsLoadingOrder(true);
      setError(null);
      try {
        const result = await getOrder(params.id);
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
  }, [user, params.id]);

  if (isLoading || !user || user.role !== "CUSTOMER") {
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
        <Link href="/orders" className="text-sm font-medium text-navy-900 underline">
          Back to orders
        </Link>
      </PageShell>
    );
  }

  return (
    <PageShell size="md">
      <Link href="/orders" className="text-sm font-medium text-navy-900 underline">
        Back to orders
      </Link>

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
            <h2 className="text-sm font-semibold text-text-muted">Shipping</h2>
            <p className="mt-2 text-sm text-text-primary">{order.shipping.recipient_name}</p>
            <p className="text-sm text-text-primary">{order.shipping.address_line}</p>
            <p className="text-sm text-text-primary">
              {order.shipping.city}, {order.shipping.region} {order.shipping.postal_code}
            </p>
            <p className="text-sm text-text-primary">{order.shipping.country}</p>
            <p className="text-sm text-text-primary">{order.shipping.phone}</p>
          </div>

          <div>
            <h2 className="text-sm font-semibold text-text-muted">Payment</h2>
            <p className="mt-2 text-sm capitalize text-text-primary">
              {order.payment.method.replace("_", " ")}
            </p>
            <p className="text-sm text-text-primary">{order.payment.status}</p>
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
                      {item.quantity} &times; ${item.unit_price}
                    </p>
                    <Pill tone={statusToTone(item.status)}>{item.status}</Pill>
                  </div>
                  <p className="font-medium text-text-primary">${item.subtotal}</p>
                </div>
              </Card>
            ))}
          </ul>
        </div>

        <div className="flex justify-end border-t border-border pt-6">
          <p className="text-lg font-semibold text-text-primary">Total: ${order.total}</p>
        </div>
      </Card>
    </PageShell>
  );
}
