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
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Pill, statusToTone } from "@/components/ui/pill";
import { ErrorText, LoadingText, EmptyText } from "@/components/ui/status-text";

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
                      {item.quantity} &times; ${item.unit_price}
                    </p>
                    <div className="mt-1">
                      <Pill tone={statusToTone(item.status)}>{item.status}</Pill>
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
