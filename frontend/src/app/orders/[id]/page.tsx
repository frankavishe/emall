"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { ApiError, getOrder, type OrderDetail } from "@/lib/api-client";

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
      <main className="mx-auto flex min-h-screen max-w-3xl items-center justify-center px-6">
        <p className="text-sm text-black/60">Loading…</p>
      </main>
    );
  }

  if (isLoadingOrder) {
    return (
      <main className="mx-auto flex min-h-screen max-w-3xl items-center justify-center px-6">
        <p className="text-sm text-black/60">Loading order…</p>
      </main>
    );
  }

  if (error || !order) {
    return (
      <main className="mx-auto flex min-h-screen max-w-3xl flex-col items-center justify-center px-6 py-12">
        <p className="mb-4 text-sm text-red-600">{error ?? "Order not found."}</p>
        <Link href="/orders" className="text-sm font-medium underline">
          Back to orders
        </Link>
      </main>
    );
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col px-6 py-12">
      <Link href="/orders" className="mb-6 text-sm font-medium underline">
        Back to orders
      </Link>

      <h1 className="text-2xl font-semibold">Order #{order.id}</h1>
      <p className="mt-1 text-sm text-black/60">
        Placed {new Date(order.placed_at).toLocaleString()} &middot; {order.status}
      </p>

      <div className="mt-6 grid grid-cols-1 gap-8 md:grid-cols-2">
        <div>
          <h2 className="text-sm font-semibold text-black/60">Shipping</h2>
          <p className="mt-2 text-sm">{order.shipping.recipient_name}</p>
          <p className="text-sm">{order.shipping.address_line}</p>
          <p className="text-sm">
            {order.shipping.city}, {order.shipping.region} {order.shipping.postal_code}
          </p>
          <p className="text-sm">{order.shipping.country}</p>
          <p className="text-sm">{order.shipping.phone}</p>
        </div>

        <div>
          <h2 className="text-sm font-semibold text-black/60">Payment</h2>
          <p className="mt-2 text-sm capitalize">{order.payment.method.replace("_", " ")}</p>
          <p className="text-sm">{order.payment.status}</p>
        </div>
      </div>

      <h2 className="mt-8 text-sm font-semibold text-black/60">Items</h2>
      <ul className="mt-2 flex flex-col gap-4">
        {order.items.map((item) => (
          <li key={item.id} className="rounded-md border border-black/15 p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="font-medium">{item.product.name}</p>
                <p className="text-sm text-black/60">Sold by {item.shop_name}</p>
                <p className="mt-1 text-sm text-black/60">
                  {item.quantity} &times; ${item.unit_price}
                </p>
                <p className="mt-1 text-sm text-black/60">Status: {item.status}</p>
              </div>
              <p className="font-medium">${item.subtotal}</p>
            </div>
          </li>
        ))}
      </ul>

      <div className="mt-6 flex justify-end border-t border-black/15 pt-6">
        <p className="text-lg font-semibold">Total: ${order.total}</p>
      </div>
    </main>
  );
}
