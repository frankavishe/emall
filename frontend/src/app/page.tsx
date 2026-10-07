"use client";

import { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useAuth, type Shop } from "@/lib/auth-context";
import {
  listVendorOrderItems,
  listAdminShops,
  listAdminOrderItems,
  listRiderDeliveries,
  getFinanceSummary,
  getVendorEarnings,
  ApiError,
  type VendorOrderItem,
  type AdminOrderItem,
} from "@/lib/api-client";
import { ProductCatalog } from "@/components/product-catalog";
import { PromoSlideshow } from "@/components/promo-slideshow";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { StatCard } from "@/components/ui/stat-card";
import { Button } from "@/components/ui/button";
import { Pill, statusToTone } from "@/components/ui/pill";
import { ActivityRow } from "@/components/ui/activity-row";
import { LoadingText, ErrorText, EmptyText } from "@/components/ui/status-text";
import type { OrderStatusDatum } from "@/components/charts/order-status-bar-chart";
import { ShopLogo } from "@/components/shop-logo";
import { formatCurrency } from "@/lib/currency";
import { useApi } from "@/lib/use-api";

const OrderStatusBarChart = dynamic(
  () => import("@/components/charts/order-status-bar-chart").then((mod) => mod.OrderStatusBarChart),
  { ssr: false },
);
const RadialGauge = dynamic(
  () => import("@/components/charts/radial-gauge").then((mod) => mod.RadialGauge),
  { ssr: false },
);

const ORDER_SAMPLE_SIZE = 100;
const RECENT_ORDER_COUNT = 5;
const ORDER_STATUSES = ["PENDING", "PROCESSING", "SHIPPED", "DELIVERED", "CANCELLED"];

function groupByStatus(items: { status: string }[]): OrderStatusDatum[] {
  const counts = new Map<string, number>();
  for (const status of ORDER_STATUSES) counts.set(status, 0);
  for (const item of items) {
    counts.set(item.status, (counts.get(item.status) ?? 0) + 1);
  }
  return ORDER_STATUSES.map((status) => ({ status, count: counts.get(status) ?? 0 }));
}

function GuestHomepage() {
  return (
    <PageShell size="xl">
      <Card variant="hero" className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">The Mall</h1>
          <p className="text-sm text-text-inverse/70">
            Products from independent shops, all in one place.
          </p>
        </div>
        <div className="flex gap-3">
          <Button variant="secondary" asChild>
            <Link href="/login">Log in</Link>
          </Button>
          <Button variant="primary" className="bg-teal-400 text-navy-900 hover:bg-teal-300" asChild>
            <Link href="/register">Register</Link>
          </Button>
        </div>
      </Card>

      <PromoSlideshow />

      <ProductCatalog />
    </PageShell>
  );
}

function CustomerHomepage() {
  return (
    <PageShell size="xl">
      <Card variant="hero" className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold">Welcome back</h1>
        <div className="flex gap-3">
          <Button variant="primary" className="bg-teal-400 text-navy-900 hover:bg-teal-300" asChild>
            <Link href="/cart">View cart</Link>
          </Button>
          <Button variant="secondary" asChild>
            <Link href="/orders">View orders</Link>
          </Button>
        </div>
      </Card>

      <PromoSlideshow />

      <ProductCatalog />
    </PageShell>
  );
}

function useVendorOrders(shouldFetch: boolean) {
  const [orders, setOrders] = useState<VendorOrderItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!shouldFetch) {
      return;
    }
    let cancelled = false;

    async function load() {
      setIsLoading(true);
      setError(null);
      try {
        const response = await listVendorOrderItems(1, ORDER_SAMPLE_SIZE);
        if (!cancelled) {
          setOrders(response.results);
          setTotalCount(response.count);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof ApiError ? err.message : "Something went wrong. Please try again.",
          );
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [shouldFetch]);

  return { orders, totalCount, isLoading, error };
}

function VendorHomepage({ shop }: { shop: Shop | undefined }) {
  const isApproved = shop?.status === "APPROVED";
  const { orders, totalCount, isLoading, error } = useVendorOrders(isApproved);

  const recent = orders.slice(0, RECENT_ORDER_COUNT);
  // `orders` is at most a ORDER_SAMPLE_SIZE-row sample (not every order item), so the
  // pending/delivered figures below are sampled ratios, not exact counts, once a shop
  // has more open items than the sample size.
  const pendingCount = orders.filter((item) => item.status === "PENDING").length;
  const deliveredCount = orders.filter((item) => item.status === "DELIVERED").length;
  const deliveredRate = orders.length > 0 ? Math.round((deliveredCount / orders.length) * 100) : 0;
  const chartData = useMemo(() => groupByStatus(orders), [orders]);

  return (
    <PageShell size="xl">
      <Card className="flex flex-col items-start gap-4">
        <div className="flex items-center gap-3">
          {shop && <ShopLogo url={shop.logo_url} name={shop.name} size="lg" />}
          <h1 className="text-2xl font-semibold text-text-primary">Your shop</h1>
        </div>
        {!shop ? (
          <>
            <p className="text-text-muted">You haven&apos;t requested a shop yet.</p>
            <Button asChild>
              <Link href="/account">Request a shop</Link>
            </Button>
          </>
        ) : shop.status === "PENDING" ? (
          <p className="text-text-muted">
            <span className="font-medium text-text-primary">{shop.name}</span> is pending approval.
          </p>
        ) : shop.status === "REJECTED" ? (
          <>
            <p className="text-text-muted">
              <span className="font-medium text-text-primary">{shop.name}</span>&apos;s request was
              rejected.
            </p>
            <Button variant="secondary" asChild>
              <Link href="/account">Go to account</Link>
            </Button>
          </>
        ) : (
          <>
            <p className="text-text-muted">
              <span className="font-medium text-text-primary">{shop.name}</span> is approved.
            </p>
            <Button asChild>
              <Link href="/vendor/products">Manage products</Link>
            </Button>
          </>
        )}
      </Card>

      {isApproved &&
        (isLoading ? (
          <LoadingText>Loading dashboard…</LoadingText>
        ) : error ? (
          <ErrorText>{error}</ErrorText>
        ) : (
          <>
            <VendorBalanceStrip />

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <StatCard variant="hero" label="Total orders" value={totalCount} />
              <StatCard label="Pending fulfillment" value={pendingCount} />
              <StatCard
                label="Delivered rate"
                value={`${deliveredRate}%`}
                trend={{ text: `${deliveredCount} delivered`, tone: "positive" }}
              />
            </div>

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <Card>
                <h2 className="mb-4 text-sm font-semibold text-text-primary">Orders by status</h2>
                <OrderStatusBarChart data={chartData} />
              </Card>
              <Card>
                <h2 className="mb-4 text-sm font-semibold text-text-primary">Delivered orders</h2>
                <RadialGauge value={deliveredRate} caption="Delivered rate" />
              </Card>
            </div>

            <Card>
              <h2 className="mb-2 text-sm font-semibold text-text-primary">Recent orders</h2>
              {recent.length === 0 ? (
                <EmptyText>No orders yet.</EmptyText>
              ) : (
                <ul className="flex flex-col divide-y divide-border">
                  {recent.map((item) => (
                    <ActivityRow
                      key={item.id}
                      name={item.product.name}
                      description={`Qty ${item.quantity}`}
                      badge={<Pill tone={statusToTone(item.status)}>{item.status}</Pill>}
                    />
                  ))}
                </ul>
              )}
            </Card>
          </>
        ))}
    </PageShell>
  );
}

function useAdminSummary() {
  const [pendingCount, setPendingCount] = useState<number | null>(null);
  const [approvedCount, setApprovedCount] = useState<number | null>(null);
  const [rejectedCount, setRejectedCount] = useState<number | null>(null);
  const [orders, setOrders] = useState<AdminOrderItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setIsLoading(true);
      setError(null);
      try {
        const [pendingResponse, approvedResponse, rejectedResponse, ordersResponse] =
          await Promise.all([
            listAdminShops("PENDING", 1),
            listAdminShops("APPROVED", 1),
            listAdminShops("REJECTED", 1),
            listAdminOrderItems(1, ORDER_SAMPLE_SIZE),
          ]);
        if (!cancelled) {
          setPendingCount(pendingResponse.count);
          setApprovedCount(approvedResponse.count);
          setRejectedCount(rejectedResponse.count);
          setOrders(ordersResponse.results);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof ApiError ? err.message : "Something went wrong. Please try again.",
          );
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  return { pendingCount, approvedCount, rejectedCount, orders, isLoading, error };
}

/** Mall money at a glance; full breakdown on /admin/finance. */
function AdminFinanceStrip() {
  const summary = useApi(() => getFinanceSummary(), "admin-finance", true);
  const figures = summary.data;
  if (!figures) return summary.error ? <ErrorText>{summary.error}</ErrorText> : null;
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
      <StatCard label="Customer payments" value={formatCurrency(figures.gross_sales)} />
      <StatCard
        label="Mall commission earned"
        value={formatCurrency(figures.commission_earned)}
        trend={{ text: `+${formatCurrency(figures.commission_pending)} pending`, tone: "positive" }}
      />
      <Link href="/admin/finance" className="contents">
        <StatCard
          label="Owed to shops now"
          value={formatCurrency(figures.available_balance)}
          trend={{ text: "pay out →" }}
        />
      </Link>
    </div>
  );
}

/** The vendor's money across all their shops; details on /vendor/earnings. */
function VendorBalanceStrip() {
  const earnings = useApi(getVendorEarnings, "vendor-earnings", true);
  if (!earnings.data) return null;
  const total = (key: "available_balance" | "pending_earnings" | "paid_out") =>
    earnings.data!.reduce((sum, shop) => sum + Number(shop[key]), 0);
  return (
    <Link href="/vendor/earnings" className="grid grid-cols-1 gap-4 sm:grid-cols-3">
      <StatCard label="Available balance" value={formatCurrency(total("available_balance"))} />
      <StatCard label="Pending delivery" value={formatCurrency(total("pending_earnings"))} />
      <StatCard label="Paid to you" value={formatCurrency(total("paid_out"))} />
    </Link>
  );
}

function AdministratorHomepage() {
  const { pendingCount, approvedCount, rejectedCount, orders, isLoading, error } =
    useAdminSummary();

  const recent = orders.slice(0, RECENT_ORDER_COUNT);
  const chartData = useMemo(() => groupByStatus(orders), [orders]);
  const totalShops = (pendingCount ?? 0) + (approvedCount ?? 0) + (rejectedCount ?? 0);
  const approvalRate = totalShops > 0 ? Math.round(((approvedCount ?? 0) / totalShops) * 100) : 0;

  return (
    <PageShell size="xl">
      {isLoading ? (
        <LoadingText>Loading dashboard…</LoadingText>
      ) : error ? (
        <ErrorText>{error}</ErrorText>
      ) : (
        <>
          <AdminFinanceStrip />

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <StatCard
              variant="hero"
              label="Pending shop approvals"
              value={pendingCount}
              trend={{ text: "needs review" }}
            />
            <StatCard label="Approved shops" value={approvedCount} />
            <StatCard label="Rejected shops" value={rejectedCount} />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Card>
              <h2 className="mb-4 text-sm font-semibold text-text-primary">Orders by status</h2>
              <OrderStatusBarChart data={chartData} />
            </Card>
            <Card>
              <h2 className="mb-4 text-sm font-semibold text-text-primary">Shop approval rate</h2>
              <RadialGauge value={approvalRate} caption="Approved shops" />
            </Card>
          </div>

          <Card>
            <div className="mb-2 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-text-primary">Recent orders</h2>
              <Link href="/admin/orders" className="text-sm font-medium text-brand-text underline">
                View all orders
              </Link>
            </div>
            {recent.length === 0 ? (
              <EmptyText>No orders yet.</EmptyText>
            ) : (
              <ul className="flex flex-col divide-y divide-border">
                {recent.map((item) => (
                  <ActivityRow
                    key={item.id}
                    name={item.product.name}
                    description={`${item.shop.name} · Qty ${item.quantity}`}
                    badge={<Pill tone={statusToTone(item.status)}>{item.status}</Pill>}
                  />
                ))}
              </ul>
            )}
          </Card>

          <Button variant="secondary" asChild className="self-start">
            <Link href="/admin/shops">Review shop approvals</Link>
          </Button>
        </>
      )}
    </PageShell>
  );
}

function useRiderSummary() {
  const [toPickUp, setToPickUp] = useState<number | null>(null);
  const [onTheWay, setOnTheWay] = useState<number | null>(null);
  const [completed, setCompleted] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setIsLoading(true);
      setError(null);
      try {
        const [active, done] = await Promise.all([
          listRiderDeliveries("active"),
          listRiderDeliveries("completed"),
        ]);
        if (!cancelled) {
          // A rider rarely has more than a page of active deliveries; the counts below are
          // from the first page, which the deliveries page paginates through in full.
          setToPickUp(active.results.filter((d) => d.status === "PROCESSING").length);
          setOnTheWay(active.results.filter((d) => d.status === "SHIPPED").length);
          setCompleted(done.count);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof ApiError ? err.message : "Something went wrong. Please try again.",
          );
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  return { toPickUp, onTheWay, completed, isLoading, error };
}

function RiderHomepage() {
  const { toPickUp, onTheWay, completed, isLoading, error } = useRiderSummary();

  return (
    <PageShell size="xl">
      <Card variant="hero" className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold">Ready to ride</h1>
        <Button variant="primary" className="bg-teal-400 text-navy-900 hover:bg-teal-300" asChild>
          <Link href="/rider/deliveries">View deliveries</Link>
        </Button>
      </Card>

      {isLoading ? (
        <LoadingText>Loading deliveries…</LoadingText>
      ) : error ? (
        <ErrorText>{error}</ErrorText>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <StatCard
            variant="hero"
            label="To pick up"
            value={toPickUp}
            trend={{ text: "waiting at shops" }}
          />
          <StatCard label="On the way" value={onTheWay} />
          <StatCard label="Completed" value={completed} />
        </div>
      )}
    </PageShell>
  );
}

export default function Home() {
  const { user, isLoading, activeRole } = useAuth();

  if (isLoading) {
    return (
      <PageShell size="lg" className="min-h-screen items-center justify-center">
        <LoadingText>Loading…</LoadingText>
      </PageShell>
    );
  }

  if (!user) {
    return <GuestHomepage />;
  }

  if (activeRole === "CUSTOMER") {
    return <CustomerHomepage />;
  }

  if (activeRole === "VENDOR") {
    return <VendorHomepage shop={user.shops?.[0]} />;
  }

  if (activeRole === "RIDER") {
    return <RiderHomepage />;
  }

  return <AdministratorHomepage />;
}
