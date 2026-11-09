"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { hasRole, useAuth } from "@/lib/auth-context";
import { useLiveRefresh } from "@/lib/realtime";
import {
  ApiError,
  assignOrderItemRider,
  errorMessage,
  listAdminOrderItems,
  listAdminRiders,
  paymentMethodLabel,
  type AdminOrderItem,
  type AdminRider,
  type PaginatedResponse,
  updateOrderItemStatus,
} from "@/lib/api-client";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Pill, statusToTone } from "@/components/ui/pill";
import { ErrorText, LoadingText, EmptyText } from "@/components/ui/status-text";
import { inputClassName } from "@/components/ui/form-field";
import { formatCurrency } from "@/lib/currency";
import { MapLink } from "@/components/map-link";
import { cn } from "@/lib/cn";

// Lines a rider can be assigned to (mirrors `orders.services.ASSIGNABLE_STATUSES`).
const ASSIGNABLE_STATUSES = new Set(["PROCESSING", "SHIPPED"]);
const RIDER_LIST_SIZE = 100;

// Mirrors backend/apps/orders/services.py's _VALID_TRANSITIONS — server-validated regardless,
// this only constrains which buttons are offered.
const NEXT_STATUSES: Record<string, string[]> = {
  PENDING: ["PROCESSING", "CANCELLED"],
  PROCESSING: ["SHIPPED", "CANCELLED"],
  SHIPPED: ["DELIVERED"],
  DELIVERED: [],
  CANCELLED: [],
};

/** Who ordered, where it goes and how it's paid: the order-level details of a line. */
function OrderDetails({ item }: { item: AdminOrderItem }) {
  const { order } = item;
  return (
    <dl className="mt-2 grid grid-cols-1 gap-x-6 gap-y-1 rounded-control bg-hover/60 p-3 text-sm sm:grid-cols-2">
      <div>
        <dt className="text-xs font-medium uppercase tracking-wide text-text-muted">Customer</dt>
        <dd className="text-text-primary">
          {order.customer.name}
          {order.customer.is_guest && <span className="text-text-muted"> (guest)</span>}
        </dd>
        <dd className="break-all text-text-muted">{order.customer.email}</dd>
      </div>
      <div>
        <dt className="text-xs font-medium uppercase tracking-wide text-text-muted">Deliver to</dt>
        <dd className="text-text-primary">
          {order.recipient_name} &middot; {order.phone}
        </dd>
        <dd className="text-text-muted">
          {order.address_line}, {order.city}{" "}
          <MapLink latitude={order.latitude} longitude={order.longitude}>
            Map
          </MapLink>
        </dd>
      </div>
      <div>
        <dt className="text-xs font-medium uppercase tracking-wide text-text-muted">Payment</dt>
        <dd className="flex flex-wrap items-center gap-2 text-text-primary">
          {order.payment ? (
            <>
              {paymentMethodLabel(order.payment.method)}
              <Pill tone={statusToTone(order.payment.status)}>{order.payment.status}</Pill>
            </>
          ) : (
            <span className="text-text-muted">No payment record</span>
          )}
        </dd>
      </div>
      <div>
        <dt className="text-xs font-medium uppercase tracking-wide text-text-muted">Order total</dt>
        <dd className="text-text-primary">
          {formatCurrency(order.total)}
          <span className="text-text-muted">
            {" "}
            &middot; {order.line_count} line{order.line_count === 1 ? "" : "s"}
          </span>
        </dd>
      </div>
    </dl>
  );
}

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
  const [statusPendingId, setStatusPendingId] = useState<number | null>(null);

  useEffect(() => {
    if (!isLoading && (!user || !hasRole(user, "ADMINISTRATOR"))) {
      router.replace(user ? "/forbidden" : "/login");
    }
  }, [isLoading, user, router]);

  const { version: liveVersion, takeQuiet } = useLiveRefresh(
    ["order.created", "order.updated", "payment.updated"],
    {
      enabled: hasRole(user, "ADMINISTRATOR"),
    },
  );

  useEffect(() => {
    if (!hasRole(user, "ADMINISTRATOR")) return;
    let cancelled = false;
    // A live update refetches in place: no spinner, and a failure keeps what's shown.
    const quiet = takeQuiet();

    async function run() {
      if (!quiet) {
        setIsLoadingItems(true);
        setError(null);
      }
      try {
        const result = await listAdminOrderItems(page);
        if (!cancelled) setItems(result);
      } catch (err) {
        if (!cancelled && !quiet) {
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
  }, [user, page, liveVersion, takeQuiet]);

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

  function replaceItem(updated: AdminOrderItem) {
    setItems((prev) =>
      prev
        ? { ...prev, results: prev.results.map((i) => (i.id === updated.id ? updated : i)) }
        : prev,
    );
  }

  async function handleAssign(item: AdminOrderItem, riderId: number | null) {
    setAssigningId(item.id);
    setError(null);
    try {
      replaceItem(await assignOrderItemRider(item.id, riderId));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setAssigningId(null);
    }
  }

  async function handleStatus(item: AdminOrderItem, newStatus: string) {
    setStatusPendingId(item.id);
    setError(null);
    try {
      replaceItem(await updateOrderItemStatus(item.id, newStatus));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setStatusPendingId(null);
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
              <Card
                as="li"
                key={item.id}
                padding="sm"
                className={cn(item.status === "PENDING" && "border-l-4 border-l-teal-400")}
              >
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0">
                    <p className="font-medium text-text-primary">{item.product.name}</p>
                    <p className="text-sm text-text-muted">
                      <Link
                        href={`/admin/orders/${item.order_id}`}
                        className="font-medium text-text-primary underline"
                      >
                        Order #{item.order_id}
                      </Link>{" "}
                      &middot; Sold by {item.shop.name} &middot; Placed{" "}
                      {new Date(item.order.placed_at).toLocaleString()}
                    </p>
                    <p className="text-sm text-text-muted">
                      {item.quantity} &times; {formatCurrency(item.unit_price)}
                    </p>
                    <div className="mt-1">
                      <Pill tone={statusToTone(item.status)}>{item.status}</Pill>
                    </div>
                    <OrderDetails item={item} />
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

                  <div className="flex shrink-0 flex-wrap gap-2 sm:flex-col sm:items-end">
                    {(NEXT_STATUSES[item.status] ?? []).map((nextStatus) => (
                      <Button
                        key={nextStatus}
                        variant={nextStatus === "CANCELLED" ? "danger" : "secondary"}
                        size="sm"
                        disabled={statusPendingId === item.id}
                        onClick={() => handleStatus(item, nextStatus)}
                      >
                        Mark {nextStatus.charAt(0) + nextStatus.slice(1).toLowerCase()}
                      </Button>
                    ))}
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setExpandedId((prev) => (prev === item.id ? null : item.id))}
                    >
                      {expandedId === item.id ? "Hide history" : "Show history"}
                    </Button>
                  </div>
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
