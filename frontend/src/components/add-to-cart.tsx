"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch, ApiError } from "@/lib/api-client";
import { useCart } from "@/lib/cart-context";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import { formatCurrency } from "@/lib/currency";

type Feedback = { kind: "success"; quantity: number } | { kind: "error"; message: string } | null;

const ADDED_FLASH_MS = 2000;

/** DRF field errors arrive as `{ quantity: ["Only 3 available."] }`; surface the first one. */
function addToCartErrorMessage(err: unknown): string {
  if (!(err instanceof ApiError)) return "Something went wrong. Please try again.";
  if (err.body && typeof err.body === "object" && !("detail" in err.body)) {
    const first = Object.values(err.body as Record<string, unknown>).flat()[0];
    if (typeof first === "string") return first;
  }
  return err.message;
}

function Spinner() {
  return (
    <span
      aria-hidden
      className="h-4 w-4 animate-spin rounded-full border-2 border-current border-r-transparent"
    />
  );
}

function CartIcon() {
  return (
    <svg
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.6}
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-4 w-4"
      aria-hidden
    >
      <path d="M2.5 3h2l1.8 9.2a1.5 1.5 0 0 0 1.5 1.2h6.6a1.5 1.5 0 0 0 1.5-1.2L17 6.5H5.4" />
      <circle cx="8" cy="16.5" r="1" />
      <circle cx="14.5" cy="16.5" r="1" />
    </svg>
  );
}

/** Quantity stepper + add-to-cart button, with inline success/error feedback. */
export function AddToCart({
  productId,
  productName,
  price,
}: {
  productId: number;
  productName: string;
  price: string;
}) {
  const { refreshCart } = useCart();
  // The draft lets the field be cleared while typing; `quantity` is the committed value.
  const [quantityDraft, setQuantityDraft] = useState("1");
  const quantity = Math.max(1, Number.parseInt(quantityDraft, 10) || 1);
  const [isAdding, setIsAdding] = useState(false);
  const [justAdded, setJustAdded] = useState(false);
  const [feedback, setFeedback] = useState<Feedback>(null);

  useEffect(() => {
    if (!justAdded) return;
    const timer = setTimeout(() => setJustAdded(false), ADDED_FLASH_MS);
    return () => clearTimeout(timer);
  }, [justAdded]);

  function changeQuantity(next: string) {
    setQuantityDraft(next);
    // A stale error ("only 2 left") shouldn't linger once the shopper adjusts the amount.
    if (feedback?.kind === "error") setFeedback(null);
  }

  async function handleAdd() {
    setIsAdding(true);
    setFeedback(null);
    try {
      await apiFetch("/api/cart/items", {
        method: "POST",
        body: JSON.stringify({ product_id: productId, quantity }),
      });
      setFeedback({ kind: "success", quantity });
      setJustAdded(true);
      setQuantityDraft("1");
      void refreshCart();
    } catch (err) {
      setFeedback({
        kind: "error",
        message: addToCartErrorMessage(err),
      });
    } finally {
      setIsAdding(false);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center rounded-pill border border-border bg-card">
          <button
            type="button"
            aria-label="Decrease quantity"
            disabled={quantity <= 1 || isAdding}
            onClick={() => changeQuantity(String(quantity - 1))}
            className="flex h-10 w-10 items-center justify-center rounded-pill text-lg text-text-primary hover:bg-hover disabled:pointer-events-none disabled:opacity-40"
          >
            −
          </button>
          <input
            type="text"
            inputMode="numeric"
            aria-label="Quantity"
            value={quantityDraft}
            disabled={isAdding}
            onChange={(event) => changeQuantity(event.target.value.replace(/\D/g, ""))}
            onBlur={() => setQuantityDraft(String(quantity))}
            // Grows with the digits typed so large quantities aren't clipped.
            style={{ width: `${Math.max(2, quantityDraft.length) + 1}ch` }}
            className="bg-transparent text-center text-sm font-medium text-text-primary outline-none"
          />
          <button
            type="button"
            aria-label="Increase quantity"
            disabled={isAdding}
            onClick={() => changeQuantity(String(quantity + 1))}
            className="flex h-10 w-10 items-center justify-center rounded-pill text-lg text-text-primary hover:bg-hover disabled:pointer-events-none disabled:opacity-40"
          >
            +
          </button>
        </div>

        <Button
          disabled={isAdding}
          onClick={() => void handleAdd()}
          className={cn(
            "h-10 min-w-48 flex-1 px-6",
            justAdded && "bg-status-delivered hover:bg-status-delivered",
          )}
        >
          {isAdding ? (
            <>
              <Spinner />
              Adding…
            </>
          ) : justAdded ? (
            <>✓ Added to cart</>
          ) : (
            <>
              <CartIcon />
              Add to cart · {formatCurrency(Number(price) * quantity)}
            </>
          )}
        </Button>
      </div>

      {feedback?.kind === "success" && (
        <div
          role="status"
          className="flex flex-wrap items-center justify-between gap-3 rounded-control border border-status-delivered/30 bg-status-delivered/10 px-4 py-3"
        >
          <p className="text-sm text-text-primary">
            <span className="font-semibold">
              {feedback.quantity} × {productName}
            </span>{" "}
            added to your cart.
          </p>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={() => setFeedback(null)}>
              Continue shopping
            </Button>
            <Button variant="secondary" size="sm" asChild>
              <Link href="/cart">View cart →</Link>
            </Button>
          </div>
        </div>
      )}

      {feedback?.kind === "error" && (
        <p
          role="alert"
          className="rounded-control border border-status-cancelled/30 bg-status-cancelled/10 px-4 py-3 text-sm text-status-cancelled"
        >
          {feedback.message}
        </p>
      )}
    </div>
  );
}
