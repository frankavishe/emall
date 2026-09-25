"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth, type Shop } from "@/lib/auth-context";
import {
  listVendorOrderItems,
  listAdminShops,
  listAdminOrderItems,
  ApiError,
  type VendorOrderItem,
  type AdminOrderItem,
} from "@/lib/api-client";
import { ProductCatalog } from "@/components/product-catalog";

const RECENT_ORDER_COUNT = 5;

function GuestHomepage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-6xl flex-col gap-6 px-6 py-6">
      <section className="flex flex-wrap items-center justify-between gap-3 border-b border-black/10 pb-4">
        <div>
          <h1 className="text-xl font-semibold">The Mall</h1>
          <p className="text-sm text-black/60">
            Products from independent shops, all in one place.
          </p>
        </div>
        <div className="flex gap-3">
          <Link
            href="/login"
            className="rounded-md bg-black px-4 py-2 text-sm font-medium text-white"
          >
            Log in
          </Link>
          <Link
            href="/register"
            className="rounded-md border border-black/15 px-4 py-2 text-sm font-medium"
          >
            Register
          </Link>
        </div>
      </section>

      <ProductCatalog />
    </main>
  );
}

function CustomerHomepage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-6xl flex-col gap-6 px-6 py-6">
      <section className="flex flex-wrap items-center justify-between gap-3 border-b border-black/10 pb-4">
        <h1 className="text-xl font-semibold">Welcome back</h1>
        <div className="flex gap-3">
          <Link
            href="/cart"
            className="rounded-md bg-black px-4 py-2 text-sm font-medium text-white"
          >
            View cart
          </Link>
          <Link
            href="/orders"
            className="rounded-md border border-black/15 px-4 py-2 text-sm font-medium"
          >
            View orders
          </Link>
        </div>
      </section>

      <ProductCatalog />
    </main>
  );
}

function useVendorOrders(shouldFetch: boolean) {
  const [orders, setOrders] = useState<VendorOrderItem[]>([]);
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
        const response = await listVendorOrderItems(1, RECENT_ORDER_COUNT);
        if (!cancelled) setOrders(response.results);
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

  return { orders, isLoading, error };
}

function VendorHomepage({ shop }: { shop: Shop | undefined }) {
  const isApproved = shop?.status === "APPROVED";
  const { orders, isLoading, error } = useVendorOrders(isApproved);

  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col gap-10 px-6 py-12">
      <section className="flex flex-col items-start gap-4">
        <h1 className="text-3xl font-semibold">Your shop</h1>
        {!shop ? (
          <>
            <p className="text-black/60">You haven&apos;t requested a shop yet.</p>
            <Link
              href="/account"
              className="rounded-md bg-black px-4 py-2 text-sm font-medium text-white"
            >
              Request a shop
            </Link>
          </>
        ) : shop.status === "PENDING" ? (
          <p className="text-black/60">
            <span className="font-medium text-black">{shop.name}</span> is pending approval.
          </p>
        ) : shop.status === "REJECTED" ? (
          <>
            <p className="text-black/60">
              <span className="font-medium text-black">{shop.name}</span>&apos;s request was
              rejected.
            </p>
            <Link
              href="/account"
              className="rounded-md border border-black/15 px-4 py-2 text-sm font-medium"
            >
              Go to account
            </Link>
          </>
        ) : (
          <>
            <p className="text-black/60">
              <span className="font-medium text-black">{shop.name}</span> is approved.
            </p>
            <Link
              href="/vendor/products"
              className="rounded-md bg-black px-4 py-2 text-sm font-medium text-white"
            >
              Manage products
            </Link>
          </>
        )}
      </section>

      {isApproved && (
        <section className="flex flex-col gap-4">
          <h2 className="text-xl font-semibold">Recent orders</h2>
          {isLoading ? (
            <p className="text-sm text-black/60">Loading orders…</p>
          ) : error ? (
            <p className="text-sm text-red-600">{error}</p>
          ) : orders.length === 0 ? (
            <p className="text-sm text-black/60">No orders yet.</p>
          ) : (
            <ul className="flex flex-col gap-2">
              {orders.map((item) => (
                <li key={item.id} className="rounded-md border border-black/15 p-4 text-sm">
                  <p className="font-medium">{item.product.name}</p>
                  <p className="text-black/60">
                    Qty {item.quantity} · {item.status}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </main>
  );
}

function useAdminSummary() {
  const [pendingCount, setPendingCount] = useState<number | null>(null);
  const [orders, setOrders] = useState<AdminOrderItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setIsLoading(true);
      setError(null);
      try {
        const [shopsResponse, ordersResponse] = await Promise.all([
          listAdminShops("PENDING", 1),
          listAdminOrderItems(1, RECENT_ORDER_COUNT),
        ]);
        if (!cancelled) {
          setPendingCount(shopsResponse.count);
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

  return { pendingCount, orders, isLoading, error };
}

function AdministratorHomepage() {
  const { pendingCount, orders, isLoading, error } = useAdminSummary();

  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col gap-10 px-6 py-12">
      <section className="flex flex-col items-start gap-4">
        <h1 className="text-3xl font-semibold">Admin overview</h1>
        {isLoading ? (
          <p className="text-sm text-black/60">Loading…</p>
        ) : error ? (
          <p className="text-sm text-red-600">{error}</p>
        ) : (
          <p className="text-black/60">
            <span className="font-medium text-black">{pendingCount}</span>{" "}
            {pendingCount === 1 ? "shop" : "shops"} pending approval.
          </p>
        )}
        <Link
          href="/admin/shops"
          className="rounded-md bg-black px-4 py-2 text-sm font-medium text-white"
        >
          Review shop approvals
        </Link>
      </section>

      <section className="flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold">Recent orders</h2>
          <Link href="/admin/orders" className="text-sm font-medium underline">
            View all orders
          </Link>
        </div>
        {isLoading ? (
          <p className="text-sm text-black/60">Loading orders…</p>
        ) : error ? (
          <p className="text-sm text-red-600">{error}</p>
        ) : orders.length === 0 ? (
          <p className="text-sm text-black/60">No orders yet.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {orders.map((item) => (
              <li key={item.id} className="rounded-md border border-black/15 p-4 text-sm">
                <p className="font-medium">{item.product.name}</p>
                <p className="text-black/60">
                  {item.shop.name} · Qty {item.quantity} · {item.status}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}

export default function Home() {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <main className="mx-auto flex min-h-screen max-w-5xl items-center justify-center px-6 py-12">
        <p className="text-sm text-black/60">Loading…</p>
      </main>
    );
  }

  if (!user) {
    return <GuestHomepage />;
  }

  if (user.role === "CUSTOMER") {
    return <CustomerHomepage />;
  }

  if (user.role === "VENDOR") {
    return <VendorHomepage shop={user.shops?.[0]} />;
  }

  return <AdministratorHomepage />;
}
