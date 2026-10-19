"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import { apiFetch } from "@/lib/api-client";
import { hasRole, useAuth } from "@/lib/auth-context";

type CartSummary = { items: { quantity: number }[] };

type CartContextValue = {
  /** Total units across all cart lines; drives the nav badge. */
  itemCount: number;
  refreshCart: () => Promise<void>;
  setCountFromCart: (cart: CartSummary | null) => void;
};

const CartContext = createContext<CartContextValue | null>(null);

function countItems(cart: CartSummary | null): number {
  return cart?.items.reduce((sum, item) => sum + item.quantity, 0) ?? 0;
}

export function CartProvider({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth();
  const [storedCount, setItemCount] = useState(0);
  // Guests have a cart too (guest checkout); only non-customer accounts don't.
  const canShop = !user || hasRole(user, "CUSTOMER");
  const itemCount = canShop ? storedCount : 0;

  const setCountFromCart = useCallback((cart: CartSummary | null) => {
    setItemCount(countItems(cart));
  }, []);

  const refreshCart = useCallback(async () => {
    if (!canShop) return;
    try {
      setCountFromCart(await apiFetch<CartSummary>("/api/cart"));
    } catch {
      // non-fatal — the badge just stays at its last known value
    }
  }, [canShop, setCountFromCart]);

  useEffect(() => {
    if (isLoading || !canShop) return;
    let cancelled = false;
    apiFetch<CartSummary>("/api/cart")
      .then((cart) => {
        if (!cancelled) setCountFromCart(cart);
      })
      .catch(() => {
        // non-fatal — the badge just stays hidden
      });
    return () => {
      cancelled = true;
    };
  }, [isLoading, canShop, user, setCountFromCart]);

  return (
    <CartContext.Provider value={{ itemCount, refreshCart, setCountFromCart }}>
      {children}
    </CartContext.Provider>
  );
}

export function useCart(): CartContextValue {
  const context = useContext(CartContext);
  if (!context) {
    throw new Error("useCart must be used within a CartProvider");
  }
  return context;
}
