"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import {
  ApiError,
  listVendorOrderItems,
  updateOrderItemStatus,
  type PaginatedResponse,
  type VendorOrderItem,
} from "@/lib/api-client";

// Mirrors backend/apps/orders/services.py's _VALID_TRANSITIONS — server-validated regardless,
// this only constrains which buttons are offered (plan.md T016).
const NEXT_STATUSES: Record<string, string[]> = {
  PENDING: ["PROCESSING", "CANCELLED"],
  PROCESSING: ["SHIPPED", "CANCELLED"],
  SHIPPED: ["DELIVERED"],
  DELIVERED: [],
  CANCELLED: [],
};

export default function VendorOrdersPage() {
  const router = useRouter();
  const { user, isLoading } = useAuth();
  const [items, setItems] = useState<PaginatedResponse<VendorOrderItem> | null>(null);
  const [isLoadingItems, setIsLoadingItems] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [pendingActionId, setPendingActionId] = useState<number | null>(null);

  useEffect(() => {
    if (!isLoading && (!user || user.role !== "VENDOR")) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  useEffect(() => {
    if (user?.role !== "VENDOR") return;
    let cancelled = false;

    async function run() {
      setIsLoadingItems(true);
      setError(null);
      try {
        const result = await listVendorOrderItems(page);
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

  async function refreshItems() {
    setIsLoadingItems(true);
    setError(null);
    try {
      const result = await listVendorOrderItems(page);
      setItems(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setIsLoadingItems(false);
    }
  }

  async function handleAdvance(item: VendorOrderItem, newStatus: string) {
    setPendingActionId(item.id);
    setError(null);
    try {
      await updateOrderItemStatus(item.id, newStatus);
      await refreshItems();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setPendingActionId(null);
    }
  }

  if (isLoading || !user || user.role !== "VENDOR") {
    return (
      <main className="mx-auto flex min-h-screen max-w-3xl items-center justify-center px-6">
        <p className="text-sm text-black/60">Loading…</p>
      </main>
    );
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col px-6 py-12">
      <h1 className="mb-6 text-2xl font-semibold">Order fulfillment</h1>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

      {isLoadingItems ? (
        <p className="text-sm text-black/60">Loading order lines…</p>
      ) : !items || items.results.length === 0 ? (
        <p className="text-sm text-black/60">No order lines awaiting fulfillment yet.</p>
      ) : (
        <>
          <ul className="flex flex-col gap-4">
            {items.results.map((item) => (
              <li key={item.id} className="rounded-md border border-black/15 p-4">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-medium">{item.product.name}</p>
                    <p className="text-sm text-black/60">
                      Order #{item.order_id} &middot; {item.quantity} &times; ${item.unit_price}
                    </p>
                    <p className="mt-1 text-sm text-black/60">Status: {item.status}</p>
                    <div className="mt-2 text-sm text-black/60">
                      <p>{item.shipping.recipient_name}</p>
                      <p>{item.shipping.address_line}</p>
                      <p>
                        {item.shipping.city}, {item.shipping.region} {item.shipping.postal_code}
                      </p>
                      <p>{item.shipping.country}</p>
                      <p>{item.shipping.phone}</p>
                    </div>
                  </div>

                  <div className="flex flex-col items-end gap-2">
                    {(NEXT_STATUSES[item.status] ?? []).map((nextStatus) => (
                      <button
                        key={nextStatus}
                        type="button"
                        disabled={pendingActionId === item.id}
                        onClick={() => handleAdvance(item, nextStatus)}
                        className={`rounded-md border px-3 py-1.5 text-sm font-medium disabled:opacity-50 ${
                          nextStatus === "CANCELLED"
                            ? "border-black/15 text-red-600"
                            : "border-black/15"
                        }`}
                      >
                        Mark {nextStatus.charAt(0) + nextStatus.slice(1).toLowerCase()}
                      </button>
                    ))}
                  </div>
                </div>
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
