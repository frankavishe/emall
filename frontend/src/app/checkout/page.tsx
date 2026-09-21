"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { ApiError, checkout, type ShippingDetails } from "@/lib/api-client";

type FieldErrors = Partial<Record<keyof ShippingDetails, string>>;

const EMPTY_SHIPPING: ShippingDetails = {
  recipient_name: "",
  address_line: "",
  city: "",
  region: "",
  postal_code: "",
  country: "",
  phone: "",
};

const FIELD_LABELS: Record<keyof ShippingDetails, string> = {
  recipient_name: "Recipient name",
  address_line: "Address",
  city: "City",
  region: "Region",
  postal_code: "Postal code",
  country: "Country",
  phone: "Phone",
};

export default function CheckoutPage() {
  const router = useRouter();
  const { user, isLoading } = useAuth();
  const [shipping, setShipping] = useState<ShippingDetails>(EMPTY_SHIPPING);
  const [paymentMethod, setPaymentMethod] = useState("card");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (!isLoading && (!user || user.role !== "CUSTOMER")) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  function updateField(field: keyof ShippingDetails, value: string) {
    setShipping((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setFieldErrors({});
    setIsSubmitting(true);
    try {
      const order = await checkout(shipping, paymentMethod);
      router.push(`/orders/${order.id}`);
    } catch (err) {
      if (err instanceof ApiError) {
        const body = err.body as {
          detail?: string;
          shipping?: Record<string, string[]>;
          lines?: { reason: string }[];
        } | null;
        if (body?.shipping) {
          const nextFieldErrors: FieldErrors = {};
          for (const [field, messages] of Object.entries(body.shipping)) {
            nextFieldErrors[field as keyof ShippingDetails] = messages[0];
          }
          setFieldErrors(nextFieldErrors);
          setError("Please fix the highlighted fields.");
        } else if (body?.lines?.length) {
          setError(
            `${body.detail ?? "Some items in your cart are no longer available."} Please update your cart and try again.`,
          );
        } else {
          setError(body?.detail ?? err.message);
        }
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isLoading || !user || user.role !== "CUSTOMER") {
    return (
      <main className="mx-auto flex min-h-screen max-w-lg items-center justify-center px-6">
        <p className="text-sm text-black/60">Loading…</p>
      </main>
    );
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-lg flex-col px-6 py-12">
      <h1 className="mb-6 text-2xl font-semibold">Checkout</h1>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        {(Object.keys(EMPTY_SHIPPING) as (keyof ShippingDetails)[]).map((field) => (
          <label key={field} className="flex flex-col gap-1 text-sm font-medium">
            {FIELD_LABELS[field]}
            <input
              type="text"
              required
              value={shipping[field]}
              onChange={(e) => updateField(field, e.target.value)}
              className="rounded-md border border-black/15 px-3 py-2 text-base outline-none focus:border-black/40"
            />
            {fieldErrors[field] && (
              <span className="text-xs text-red-600">{fieldErrors[field]}</span>
            )}
          </label>
        ))}

        <label className="flex flex-col gap-1 text-sm font-medium">
          Payment method
          <select
            value={paymentMethod}
            onChange={(e) => setPaymentMethod(e.target.value)}
            className="rounded-md border border-black/15 px-3 py-2 text-base outline-none focus:border-black/40"
          >
            <option value="card">Card</option>
            <option value="mobile_money">Mobile money</option>
          </select>
        </label>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button
          type="submit"
          disabled={isSubmitting}
          className="mt-2 rounded-md bg-black px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {isSubmitting ? "Placing order…" : "Place order"}
        </button>
      </form>
    </main>
  );
}
