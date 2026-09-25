"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { apiFetch, ApiError } from "@/lib/api-client";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ErrorText, LoadingText, EmptyText } from "@/components/ui/status-text";
import { formatCurrency } from "@/lib/currency";

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
      <PageShell size="md" className="min-h-screen items-center justify-center">
        <LoadingText />
      </PageShell>
    );
  }

  const hasUnavailableItem = cart?.items.some((item) => !item.is_available) ?? false;

  return (
    <PageShell size="md" title="Your cart">
      {error && <ErrorText>{error}</ErrorText>}

      {isLoadingCart ? (
        <LoadingText>Loading cart…</LoadingText>
      ) : !cart || cart.items.length === 0 ? (
        <EmptyText>
          Your cart is empty.{" "}
          <Link href="/products" className="font-medium text-navy-900 underline">
            Browse products
          </Link>
        </EmptyText>
      ) : (
        <>
          <ul className="flex flex-col gap-4">
            {cart.items.map((item) => (
              <Card as="li" key={item.id} padding="sm">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-medium text-text-primary">{item.product.name}</p>
                    <p className="text-sm text-text-muted">Sold by {item.product.shop_name}</p>
                    <p className="mt-1 text-sm text-text-muted">
                      {formatCurrency(item.unit_price)} each &middot; Subtotal: {formatCurrency(item.subtotal)}
                    </p>
                    {!item.is_available && (
                      <p className="mt-1 text-sm text-status-cancelled">
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
                      className="w-20 rounded-control border border-border px-2 py-1 text-sm"
                    />
                    <Button
                      variant="danger"
                      size="sm"
                      disabled={pendingItemId === item.id}
                      onClick={() => handleRemove(item)}
                    >
                      Remove
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </ul>

          <Card className="flex flex-col items-end gap-2">
            <div className="flex w-full items-center justify-between">
              <p className="text-lg font-semibold text-text-primary">Total: {formatCurrency(cart.total)}</p>
              {hasUnavailableItem ? (
                <Button disabled>Checkout</Button>
              ) : (
                <Button asChild>
                  <Link href="/checkout">Checkout</Link>
                </Button>
              )}
            </div>
            {hasUnavailableItem && (
              <p className="text-sm text-status-cancelled">
                Remove or adjust the unavailable item(s) above before checking out.
              </p>
            )}
          </Card>
        </>
      )}
    </PageShell>
  );
}
