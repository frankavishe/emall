"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { hasRole, useAuth } from "@/lib/auth-context";
import {
  errorMessage,
  listRiderDeliveries,
  updateDeliveryStatus,
  type PaginatedResponse,
  type RiderDelivery,
} from "@/lib/api-client";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Pill, statusToTone } from "@/components/ui/pill";
import { SegmentedToggle } from "@/components/ui/segmented-toggle";
import { ErrorText, LoadingText, EmptyText } from "@/components/ui/status-text";

type Scope = "active" | "completed";

/** The next step a rider can take on a delivery, if any. */
const NEXT_STEP: Partial<Record<string, { status: "SHIPPED" | "DELIVERED"; label: string }>> = {
  PROCESSING: { status: "SHIPPED", label: "Mark picked up" },
  SHIPPED: { status: "DELIVERED", label: "Mark delivered" },
};

const STATUS_LABEL: Record<string, string> = {
  PROCESSING: "TO PICK UP",
  SHIPPED: "ON THE WAY",
};

function DeliveryCard({
  delivery,
  isPending,
  onAdvance,
}: {
  delivery: RiderDelivery;
  isPending: boolean;
  onAdvance: (delivery: RiderDelivery, status: "SHIPPED" | "DELIVERED") => void;
}) {
  const next = NEXT_STEP[delivery.status];
  const { dropoff } = delivery;

  return (
    <Card as="li" padding="sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex flex-col gap-2">
          <div>
            <p className="font-medium text-text-primary">
              {delivery.product.name} &times; {delivery.quantity}
            </p>
            <p className="text-sm text-text-muted">Order #{delivery.order_id}</p>
          </div>

          <div className="text-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">Pick up</p>
            <p className="text-text-primary">{delivery.pickup.shop_name}</p>
          </div>

          <div className="text-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">
              Deliver to
            </p>
            <p className="text-text-primary">{dropoff.recipient_name}</p>
            <p className="text-text-muted">
              {dropoff.address_line}, {dropoff.city}, {dropoff.region}
            </p>
            <a href={`tel:${dropoff.phone}`} className="font-medium text-navy-900 underline">
              {dropoff.phone}
            </a>
          </div>
        </div>

        <div className="flex flex-col items-end gap-2">
          <Pill tone={statusToTone(delivery.status)}>
            {STATUS_LABEL[delivery.status] ?? delivery.status}
          </Pill>
          {next && (
            <Button size="sm" disabled={isPending} onClick={() => onAdvance(delivery, next.status)}>
              {next.label}
            </Button>
          )}
        </div>
      </div>
    </Card>
  );
}

export default function RiderDeliveriesPage() {
  const router = useRouter();
  const { user, isLoading } = useAuth();
  const [scope, setScope] = useState<Scope>("active");
  const [page, setPage] = useState(1);
  const [deliveries, setDeliveries] = useState<PaginatedResponse<RiderDelivery> | null>(null);
  const [isLoadingDeliveries, setIsLoadingDeliveries] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pendingId, setPendingId] = useState<number | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    if (!isLoading && (!user || !hasRole(user, "RIDER"))) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  useEffect(() => {
    if (!hasRole(user, "RIDER")) return;
    let cancelled = false;

    async function run() {
      setIsLoadingDeliveries(true);
      setError(null);
      try {
        const result = await listRiderDeliveries(scope, page);
        if (!cancelled) setDeliveries(result);
      } catch (err) {
        if (!cancelled) setError(errorMessage(err));
      } finally {
        if (!cancelled) setIsLoadingDeliveries(false);
      }
    }

    void run();
    return () => {
      cancelled = true;
    };
  }, [user, scope, page, reloadKey]);

  function handleScopeChange(next: Scope) {
    setScope(next);
    setPage(1);
  }

  async function handleAdvance(delivery: RiderDelivery, status: "SHIPPED" | "DELIVERED") {
    setPendingId(delivery.id);
    setError(null);
    try {
      await updateDeliveryStatus(delivery.id, status);
      setReloadKey((key) => key + 1);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setPendingId(null);
    }
  }

  if (isLoading || !user || !hasRole(user, "RIDER")) {
    return (
      <PageShell size="md" className="min-h-screen items-center justify-center">
        <LoadingText />
      </PageShell>
    );
  }

  return (
    <PageShell size="md" title="My deliveries">
      <SegmentedToggle
        options={[
          { value: "active", label: "ACTIVE" },
          { value: "completed", label: "COMPLETED" },
        ]}
        value={scope}
        onChange={handleScopeChange}
        className="self-start"
      />

      {error && <ErrorText>{error}</ErrorText>}

      {isLoadingDeliveries ? (
        <LoadingText>Loading deliveries…</LoadingText>
      ) : !deliveries || deliveries.results.length === 0 ? (
        <EmptyText>
          {scope === "active"
            ? "No deliveries assigned to you right now."
            : "No completed deliveries yet."}
        </EmptyText>
      ) : (
        <>
          <ul className="flex flex-col gap-4">
            {deliveries.results.map((delivery) => (
              <DeliveryCard
                key={delivery.id}
                delivery={delivery}
                isPending={pendingId === delivery.id}
                onAdvance={handleAdvance}
              />
            ))}
          </ul>

          {(deliveries.previous || deliveries.next) && (
            <div className="flex items-center justify-between">
              <Button
                variant="secondary"
                disabled={!deliveries.previous}
                onClick={() => setPage((prev) => prev - 1)}
              >
                Previous
              </Button>
              <Button
                variant="secondary"
                disabled={!deliveries.next}
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
