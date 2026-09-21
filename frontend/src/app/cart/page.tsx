"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { apiFetch, ApiError } from "@/lib/api-client";

type CartItem = {
  id: number;
  product: { id: number; name: string; shop_name: string };
  quantity: number;
  unit_price: string;
  subtotal: string;
  is_available: boolean;
  unavailable_reason: string | null;
};

type Cart = {
  id: number;
  items: CartItem[];
  total: string;
};

export default function CartPage() {
  const router = useRouter();
  const { user, isLoading } = useAuth();
  const [cart, setCart] = useState<Cart | null>(null);
  const [isLoadingCart, setIsLoadingCart] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pendingItemId, setPendingItemId] = useState<number | null>(null);

  useEffect(() => {
    if (!isLoading && (!user || user.role !== "CUSTOMER")) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  const loadCart = useCallback(async () => {
    setIsLoadingCart(true);
    setError(null);
    try {
      const result = await apiFetch<Cart>("/api/cart");
      setCart(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setIsLoadingCart(false);
    }
  }, []);

  useEffect(() => {
    if (user?.role !== "CUSTOMER") return;
    let cancelled = false;

    async function run() {
      setIsLoadingCart(true);
      setError(null);
      try {
        const result = await apiFetch<Cart>("/api/cart");
        if (!cancelled) setCart(result);
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof ApiError ? err.message : "Something went wrong. Please try again.",
          );
        }
      } finally {
        if (!cancelled) setIsLoadingCart(false);
      }
    }

    void run();
    return () => {
      cancelled = true;
    };
  }, [user]);

  async function handleQuantityChange(item: CartItem, quantity: number) {
    if (quantity < 1) return;
    setPendingItemId(item.id);
    setError(null);
    try {
      await apiFetch(`/api/cart/items/${item.id}`, {
        method: "PATCH",
        body: JSON.stringify({ quantity }),
      });
      await loadCart();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setPendingItemId(null);
    }
  }

  async function handleRemove(item: CartItem) {
    setPendingItemId(item.id);
    setError(null);
    try {
      await apiFetch(`/api/cart/items/${item.id}`, { method: "DELETE" });
      await loadCart();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setPendingItemId(null);
    }
  }

  if (isLoading || !user || user.role !== "CUSTOMER") {
    return (
      <main className="mx-auto flex min-h-screen max-w-3xl items-center justify-center px-6">
        <p className="text-sm text-black/60">Loading…</p>
      </main>
    );
  }

  const hasUnavailableItem = cart?.items.some((item) => !item.is_available) ?? false;

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col px-6 py-12">
      <h1 className="mb-6 text-2xl font-semibold">Your cart</h1>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

      {isLoadingCart ? (
        <p className="text-sm text-black/60">Loading cart…</p>
      ) : !cart || cart.items.length === 0 ? (
        <p className="text-sm text-black/60">
          Your cart is empty.{" "}
          <Link href="/products" className="font-medium underline">
            Browse products
          </Link>
        </p>
      ) : (
        <>
          <ul className="flex flex-col gap-4">
            {cart.items.map((item) => (
              <li key={item.id} className="rounded-md border border-black/15 p-4">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-medium">{item.product.name}</p>
                    <p className="text-sm text-black/60">Sold by {item.product.shop_name}</p>
                    <p className="mt-1 text-sm text-black/60">
                      ${item.unit_price} each &middot; Subtotal: ${item.subtotal}
                    </p>
                    {!item.is_available && (
                      <p className="mt-1 text-sm text-red-600">
                        Unavailable: {item.unavailable_reason}
                      </p>
                    )}
                  </div>

                  <div className="flex flex-col items-end gap-2">
                    <input
                      type="number"
                      min={1}
                      value={item.quantity}
                      disabled={pendingItemId === item.id}
                      onChange={(event) => handleQuantityChange(item, Number(event.target.value))}
                      className="w-20 rounded-md border border-black/15 px-2 py-1 text-sm"
                    />
                    <button
                      type="button"
                      disabled={pendingItemId === item.id}
                      onClick={() => handleRemove(item)}
                      className="rounded-md border border-black/15 px-3 py-1.5 text-sm font-medium text-red-600 disabled:opacity-50"
                    >
                      Remove
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>

          <div className="mt-6 flex flex-col items-end gap-2 border-t border-black/15 pt-6">
            <div className="flex w-full items-center justify-between">
              <p className="text-lg font-semibold">Total: ${cart.total}</p>
              {hasUnavailableItem ? (
                <button
                  type="button"
                  disabled
                  className="rounded-md bg-black px-4 py-2 text-sm font-medium text-white opacity-50"
                >
                  Checkout
                </button>
              ) : (
                <Link
                  href="/checkout"
                  className="rounded-md bg-black px-4 py-2 text-sm font-medium text-white"
                >
                  Checkout
                </Link>
              )}
            </div>
            {hasUnavailableItem && (
              <p className="text-sm text-red-600">
                Remove or adjust the unavailable item(s) above before checking out.
              </p>
            )}
          </div>
        </>
      )}
    </main>
  );
}
