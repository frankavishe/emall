"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { hasRole, useAuth } from "@/lib/auth-context";
import {
  ApiError,
  assignOrderItemRider,
  errorMessage,
  listAdminOrderItems,
  listAdminRiders,
  type AdminOrderItem,
  type AdminRider,
  type PaginatedResponse,
} from "@/lib/api-client";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Pill, statusToTone } from "@/components/ui/pill";
import { ErrorText, LoadingText, EmptyText } from "@/components/ui/status-text";
import { inputClassName } from "@/components/ui/form-field";
import { formatCurrency } from "@/lib/currency";

// Lines a rider can be assigned to (mirrors `orders.services.ASSIGNABLE_STATUSES`).
const ASSIGNABLE_STATUSES = new Set(["PROCESSING", "SHIPPED"]);
const RIDER_LIST_SIZE = 100;

function RiderAssignment({
  item,
  riders,
  isPending,
  onAssign,
}: {
  item: AdminOrderItem;
  riders: AdminRider[];
  isPending: boolean;
  onAssign: (item: AdminOrderItem, riderId: number | null) => void;
}) {
  const [selected, setSelected] = useState<string>(item.rider ? String(item.rider.id) : "");
  const canAssign = ASSIGNABLE_STATUSES.has(item.status);

  if (!canAssign) {
    return item.rider ? (
      <p className="text-sm text-text-muted">
        Rider: {item.rider.name} &middot; {item.rider.phone}
      </p>
    ) : null;
  }

  const changed = selected !== (item.rider ? String(item.rider.id) : "");

  return (
    <div className="flex flex-wrap items-center gap-2">
      <select
        aria-label="Rider"
        value={selected}
        onChange={(e) => setSelected(e.target.value)}
        className={`text-sm ${inputClassName}`}
      >
        <option value="">No rider</option>
        {item.rider && !riders.some((r) => r.id === item.rider?.id) && (
          <option value={item.rider.id}>{item.rider.name}</option>
        )}
        {riders.map((rider) => (
          <option key={rider.id} value={rider.id}>
            {rider.name} ({rider.active_delivery_count} active)
          </option>
        ))}
      </select>
      <Button
        variant="secondary"
        size="sm"
        disabled={isPending || !changed}
        onClick={() => onAssign(item, selected ? Number(selected) : null)}
      >
        {selected ? "Assign rider" : "Unassign"}
      </Button>
    </div>
  );
}

export default function AdminOrdersPage() {
  const router = useRouter();
  const { user, isLoading } = useAuth();
  const [items, setItems] = useState<PaginatedResponse<AdminOrderItem> | null>(null);
  const [isLoadingItems, setIsLoadingItems] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [riders, setRiders] = useState<AdminRider[]>([]);
  const [assigningId, setAssigningId] = useState<number | null>(null);

  useEffect(() => {
    if (!isLoading && (!user || !hasRole(user, "ADMINISTRATOR"))) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  useEffect(() => {
    if (!hasRole(user, "ADMINISTRATOR")) return;
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

  useEffect(() => {
    if (!hasRole(user, "ADMINISTRATOR")) return;
    let cancelled = false;

    async function run() {
      try {
        const result = await listAdminRiders({ isActive: true, limit: RIDER_LIST_SIZE });
        if (!cancelled) setRiders(result.results);
      } catch {
        // Assignment just shows no riders to pick; the order list itself still works.
      }
    }

    void run();
    return () => {
      cancelled = true;
    };
  }, [user]);

  async function handleAssign(item: AdminOrderItem, riderId: number | null) {
    setAssigningId(item.id);
    setError(null);
    try {
      const updated = await assignOrderItemRider(item.id, riderId);
      setItems((prev) =>
        prev
          ? { ...prev, results: prev.results.map((i) => (i.id === updated.id ? updated : i)) }
          : prev,
      );
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setAssigningId(null);
    }
  }

  if (isLoading || !user || !hasRole(user, "ADMINISTRATOR")) {
    return (
      <PageShell size="md" className="min-h-screen items-center justify-center">
        <LoadingText />
      </PageShell>
    );
  }

  return (
    <PageShell size="md" title="Order fulfillment oversight">
      {error && <ErrorText>{error}</ErrorText>}

      {isLoadingItems ? (
        <LoadingText>Loading order lines…</LoadingText>
      ) : !items || items.results.length === 0 ? (
        <EmptyText>No order lines yet.</EmptyText>
      ) : (
        <>
          <ul className="flex flex-col gap-4">
            {items.results.map((item) => (
              <Card as="li" key={item.id} padding="sm">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-medium text-text-primary">{item.product.name}</p>
                    <p className="text-sm text-text-muted">
                      Order #{item.order_id} &middot; Sold by {item.shop.name}
                    </p>
                    <p className="text-sm text-text-muted">
                      {item.quantity} &times; {formatCurrency(item.unit_price)}
                    </p>
                    <div className="mt-1">
                      <Pill tone={statusToTone(item.status)}>{item.status}</Pill>
                    </div>
                    <div className="mt-2">
                      <RiderAssignment
                        key={item.rider?.id ?? "none"}
                        item={item}
                        riders={riders}
                        isPending={assigningId === item.id}
                        onAssign={handleAssign}
                      />
                    </div>
                  </div>

                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => setExpandedId((prev) => (prev === item.id ? null : item.id))}
                  >
                    {expandedId === item.id ? "Hide history" : "Show history"}
                  </Button>
                </div>

                {expandedId === item.id && (
                  <div className="mt-3 border-t border-border pt-3">
                    {item.status_history.length === 0 ? (
                      <EmptyText>No status changes yet.</EmptyText>
                    ) : (
                      <ul className="flex flex-col gap-1">
                        {item.status_history.map((event, index) => (
                          <li key={index} className="text-sm text-text-muted">
                            {event.status} &middot; {new Date(event.changed_at).toLocaleString()}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
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
