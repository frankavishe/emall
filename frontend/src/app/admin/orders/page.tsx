"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import {
  ApiError,
  listAdminOrderItems,
  type AdminOrderItem,
  type PaginatedResponse,
} from "@/lib/api-client";

export default function AdminOrdersPage() {
  const router = useRouter();
  const { user, isLoading } = useAuth();
  const [items, setItems] = useState<PaginatedResponse<AdminOrderItem> | null>(null);
  const [isLoadingItems, setIsLoadingItems] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  useEffect(() => {
    if (!isLoading && (!user || user.role !== "ADMINISTRATOR")) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  useEffect(() => {
    if (user?.role !== "ADMINISTRATOR") return;
    let cancelled = false;

    async function run() {
      setIsLoadingItems(true);
      setError(null);
      try {
        const result = await listAdminOrderItems(page);
        if (!cancelled) setItems(result);
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof ApiError ? err.message : "Something went wrong. Please try again.",
          );
        }
      } finally {
        if (!cancelled) setIsLoadingItems(false);
      }
    }

    void run();
    return () => {
      cancelled = true;
    };
  }, [user, page]);

  if (isLoading || !user || user.role !== "ADMINISTRATOR") {
    return (
      <main className="mx-auto flex min-h-screen max-w-3xl items-center justify-center px-6">
        <p className="text-sm text-black/60">Loading…</p>
      </main>
    );
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col px-6 py-12">
      <h1 className="mb-6 text-2xl font-semibold">Order fulfillment oversight</h1>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

      {isLoadingItems ? (
        <p className="text-sm text-black/60">Loading order lines…</p>
      ) : !items || items.results.length === 0 ? (
        <p className="text-sm text-black/60">No order lines yet.</p>
      ) : (
        <>
          <ul className="flex flex-col gap-4">
            {items.results.map((item) => (
              <li key={item.id} className="rounded-md border border-black/15 p-4">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-medium">{item.product.name}</p>
                    <p className="text-sm text-black/60">
                      Order #{item.order_id} &middot; Sold by {item.shop.name}
                    </p>
                    <p className="text-sm text-black/60">
                      {item.quantity} &times; ${item.unit_price}
                    </p>
                    <p className="mt-1 text-sm text-black/60">Status: {item.status}</p>
                  </div>

                  <button
                    type="button"
                    onClick={() => setExpandedId((prev) => (prev === item.id ? null : item.id))}
                    className="rounded-md border border-black/15 px-3 py-1.5 text-sm font-medium"
                  >
                    {expandedId === item.id ? "Hide history" : "Show history"}
                  </button>
                </div>

                {expandedId === item.id && (
                  <div className="mt-3 border-t border-black/15 pt-3">
                    {item.status_history.length === 0 ? (
                      <p className="text-sm text-black/60">No status changes yet.</p>
                    ) : (
                      <ul className="flex flex-col gap-1">
                        {item.status_history.map((event, index) => (
                          <li key={index} className="text-sm text-black/60">
                            {event.status} &middot; {new Date(event.changed_at).toLocaleString()}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </li>
            ))}
          </ul>

          {(items.previous || items.next) && (
            <div className="mt-6 flex items-center justify-between">
              <button
                type="button"
                disabled={!items.previous}
                onClick={() => setPage((prev) => prev - 1)}
                className="rounded-md border border-black/15 px-3 py-1.5 text-sm font-medium disabled:opacity-50"
              >
                Previous
              </button>
              <button
                type="button"
                disabled={!items.next}
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
