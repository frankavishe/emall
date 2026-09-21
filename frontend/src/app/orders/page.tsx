"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { ApiError, listOrders, type OrderSummary, type PaginatedResponse } from "@/lib/api-client";

export default function OrdersPage() {
  const router = useRouter();
  const { user, isLoading } = useAuth();
  const [orders, setOrders] = useState<PaginatedResponse<OrderSummary> | null>(null);
  const [isLoadingOrders, setIsLoadingOrders] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  useEffect(() => {
    if (!isLoading && (!user || user.role !== "CUSTOMER")) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  useEffect(() => {
    if (user?.role !== "CUSTOMER") return;
    let cancelled = false;

    async function run() {
      setIsLoadingOrders(true);
      setError(null);
      try {
        const result = await listOrders(page);
        if (!cancelled) setOrders(result);
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof ApiError ? err.message : "Something went wrong. Please try again.",
          );
        }
      } finally {
        if (!cancelled) setIsLoadingOrders(false);
      }
    }

    void run();
    return () => {
      cancelled = true;
    };
  }, [user, page]);

  if (isLoading || !user || user.role !== "CUSTOMER") {
    return (
      <main className="mx-auto flex min-h-screen max-w-3xl items-center justify-center px-6">
        <p className="text-sm text-black/60">Loading…</p>
      </main>
    );
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col px-6 py-12">
      <h1 className="mb-6 text-2xl font-semibold">Your orders</h1>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

      {isLoadingOrders ? (
        <p className="text-sm text-black/60">Loading orders…</p>
      ) : !orders || orders.results.length === 0 ? (
        <p className="text-sm text-black/60">
          You haven&apos;t placed any orders yet.{" "}
          <Link href="/products" className="font-medium underline">
            Browse products
          </Link>
        </p>
      ) : (
        <>
          <ul className="flex flex-col gap-4">
            {orders.results.map((order) => (
              <li key={order.id} className="rounded-md border border-black/15 p-4">
                <Link href={`/orders/${order.id}`} className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">Order #{order.id}</p>
                    <p className="text-sm text-black/60">
                      Placed {new Date(order.placed_at).toLocaleDateString()} &middot;{" "}
                      {order.status}
                    </p>
                  </div>
                  <p className="text-lg font-semibold">${order.total}</p>
                </Link>
              </li>
            ))}
          </ul>

          {(orders.previous || orders.next) && (
            <div className="mt-6 flex items-center justify-between">
              <button
                type="button"
                disabled={!orders.previous}
                onClick={() => setPage((prev) => prev - 1)}
                className="rounded-md border border-black/15 px-3 py-1.5 text-sm font-medium disabled:opacity-50"
              >
                Previous
              </button>
              <button
                type="button"
                disabled={!orders.next}
                onClick={() => setPage((prev) => prev + 1)}
                className="rounded-md border border-black/15 px-3 py-1.5 text-sm font-medium disabled:opacity-50"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </main>
  );
}
