"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { ApiError, listOrders, type OrderSummary, type PaginatedResponse } from "@/lib/api-client";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Pill, statusToTone } from "@/components/ui/pill";
import { ErrorText, LoadingText, EmptyText } from "@/components/ui/status-text";

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
      <PageShell size="md" className="min-h-screen items-center justify-center">
        <LoadingText />
      </PageShell>
    );
  }

  return (
    <PageShell size="md" title="Your orders">
      {error && <ErrorText>{error}</ErrorText>}

      {isLoadingOrders ? (
        <LoadingText>Loading orders…</LoadingText>
      ) : !orders || orders.results.length === 0 ? (
        <EmptyText>
          You haven&apos;t placed any orders yet.{" "}
          <Link href="/products" className="font-medium text-navy-900 underline">
            Browse products
          </Link>
        </EmptyText>
      ) : (
        <>
          <ul className="flex flex-col gap-4">
            {orders.results.map((order) => (
              <Card as="li" key={order.id} padding="sm">
                <Link href={`/orders/${order.id}`} className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-text-primary">Order #{order.id}</p>
                    <p className="text-sm text-text-muted">
                      Placed {new Date(order.placed_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <Pill tone={statusToTone(order.status)}>{order.status}</Pill>
                    <p className="text-lg font-semibold text-text-primary">${order.total}</p>
                  </div>
                </Link>
              </Card>
            ))}
          </ul>

          {(orders.previous || orders.next) && (
            <div className="flex items-center justify-between">
              <Button
                variant="secondary"
                disabled={!orders.previous}
                onClick={() => setPage((prev) => prev - 1)}
              >
                Previous
              </Button>
              <Button
                variant="secondary"
                disabled={!orders.next}
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
