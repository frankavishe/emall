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
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Pill, statusToTone } from "@/components/ui/pill";
import { ErrorText, LoadingText, EmptyText } from "@/components/ui/status-text";
import { formatCurrency } from "@/lib/currency";

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
      <PageShell size="md" className="min-h-screen items-center justify-center">
        <LoadingText />
      </PageShell>
    );
  }

  return (
    <PageShell size="md" title="Order fulfillment">
      {error && <ErrorText>{error}</ErrorText>}

      {isLoadingItems ? (
        <LoadingText>Loading order lines…</LoadingText>
      ) : !items || items.results.length === 0 ? (
        <EmptyText>No order lines awaiting fulfillment yet.</EmptyText>
      ) : (
        <>
          <ul className="flex flex-col gap-4">
            {items.results.map((item) => (
              <Card as="li" key={item.id} padding="sm">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-medium text-text-primary">{item.product.name}</p>
                    <p className="text-sm text-text-muted">
                      Order #{item.order_id} &middot; {item.quantity} &times; {formatCurrency(item.unit_price)}
                    </p>
                    <div className="mt-1">
                      <Pill tone={statusToTone(item.status)}>{item.status}</Pill>
                    </div>
                    <div className="mt-2 text-sm text-text-muted">
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
                      <Button
                        key={nextStatus}
                        variant={nextStatus === "CANCELLED" ? "danger" : "secondary"}
                        size="sm"
                        disabled={pendingActionId === item.id}
                        onClick={() => handleAdvance(item, nextStatus)}
                      >
                        Mark {nextStatus.charAt(0) + nextStatus.slice(1).toLowerCase()}
                      </Button>
                    ))}
                  </div>
                </div>
              </Card>
            ))}
          </ul>

          {(items.previous || items.next) && (
            <div className="flex items-center justify-between">
              <Button
                variant="secondary"
                disabled={!items.previous}
                onClick={() => setPage((prev) => prev - 1)}
              >
                Previous
              </Button>
              <Button
                variant="secondary"
                disabled={!items.next}
                onClick={() => setPage((prev) => prev + 1)}
              >
                Next
              </Button>
            </div>
          )}
        </>
      )}
    </PageShell>
  );
}
