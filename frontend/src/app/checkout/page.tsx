"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { hasRole, useAuth } from "@/lib/auth-context";
import {
  ApiError,
  checkout,
  getDeliveryQuote,
  type DeliveryQuote,
  type LatLng,
  type ShippingAddress,
} from "@/lib/api-client";
import { formatCurrency } from "@/lib/currency";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FormField, inputClassName } from "@/components/ui/form-field";
import { ErrorText, LoadingText } from "@/components/ui/status-text";
import { LocationPicker } from "@/components/location-picker";
import { DeliverySummary } from "@/components/delivery-summary";

type FieldErrors = Partial<Record<keyof ShippingAddress, string>>;

const EMPTY_SHIPPING: ShippingAddress = {
  recipient_name: "",
  address_line: "",
  city: "",
  region: "",
  postal_code: "",
  country: "",
  phone: "",
};

const FIELD_LABELS: Record<keyof ShippingAddress, string> = {
  recipient_name: "Recipient name",
  address_line: "Address",
  city: "City",
  region: "Region",
  postal_code: "Postal code",
  country: "Country",
  phone: "Phone",
};

const QUOTE_DEBOUNCE_MS = 400;

export default function CheckoutPage() {
  const router = useRouter();
  const { user, isLoading } = useAuth();
  const [shipping, setShipping] = useState<ShippingAddress>(EMPTY_SHIPPING);
  const [pin, setPin] = useState<LatLng | null>(null);
  const [quote, setQuote] = useState<DeliveryQuote | null>(null);
  const [quoteError, setQuoteError] = useState<string | null>(null);
  const [isQuoting, setIsQuoting] = useState(false);
  const [paymentMethod, setPaymentMethod] = useState("card");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (!isLoading && (!user || !hasRole(user, "CUSTOMER"))) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  // Re-price delivery whenever the pin settles. The quote is only a preview: checkout
  // recomputes the fee on the server.
  useEffect(() => {
    if (!pin) return;
    let cancelled = false;
    const timer = setTimeout(() => {
      getDeliveryQuote(pin)
        .then((result) => {
          if (cancelled) return;
          setQuote(result);
          setQuoteError(null);
        })
        .catch((err) => {
          if (cancelled) return;
          setQuote(null);
          setQuoteError(
            err instanceof ApiError ? err.message : "Couldn't price delivery. Please try again.",
          );
        })
        .finally(() => {
          if (!cancelled) setIsQuoting(false);
        });
    }, QUOTE_DEBOUNCE_MS);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [pin]);

  function changePin(next: LatLng) {
    setPin(next);
    setIsQuoting(true);
  }

  function updateField(field: keyof ShippingAddress, value: string) {
    setShipping((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!pin) {
      setError("Set your delivery location on the map before placing the order.");
      return;
    }
    setError(null);
    setFieldErrors({});
    setIsSubmitting(true);
    try {
      const order = await checkout({ ...shipping, ...pin }, paymentMethod);
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
          let pinInvalid = false;
          for (const [field, messages] of Object.entries(body.shipping)) {
            if (field === "latitude" || field === "longitude") pinInvalid = true;
            else nextFieldErrors[field as keyof ShippingAddress] = messages[0];
          }
          setFieldErrors(nextFieldErrors);
          setError(
            pinInvalid
              ? "Set a valid delivery location on the map."
              : "Please fix the highlighted fields.",
          );
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

  if (isLoading || !user || !hasRole(user, "CUSTOMER")) {
    return (
      <PageShell size="md" className="min-h-screen items-center justify-center">
        <LoadingText />
      </PageShell>
    );
  }

  const canSubmit = !!pin && !!quote && !quoteError && !isQuoting && !isSubmitting;

  return (
    <PageShell size="md">
      <Card>
        <h1 className="mb-1 text-2xl font-semibold text-text-primary">Checkout</h1>
        <p className="mb-6 text-sm text-text-muted">
          Every MangiMall order is delivered to you. The delivery fee depends on how far each shop
          is from your location.
        </p>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {(Object.keys(EMPTY_SHIPPING) as (keyof ShippingAddress)[]).map((field) => (
            <FormField key={field} label={FIELD_LABELS[field]}>
              <input
                type="text"
                required
                value={shipping[field]}
                onChange={(e) => updateField(field, e.target.value)}
                className={inputClassName}
              />
              {fieldErrors[field] && (
                <span className="text-xs text-status-cancelled">{fieldErrors[field]}</span>
              )}
            </FormField>
          ))}

          <LocationPicker value={pin} onChange={changePin} />

          <section
            aria-label="Order summary"
            className="flex flex-col gap-2 rounded-control border border-border bg-card-muted p-4"
          >
            <h2 className="text-sm font-semibold text-text-primary">Order summary</h2>
            {!pin ? (
              <p className="text-sm text-text-muted">
                Set your delivery location to see the delivery fee.
              </p>
            ) : quoteError ? (
              <ErrorText>{quoteError}</ErrorText>
            ) : !quote ? (
              <LoadingText>Pricing delivery…</LoadingText>
            ) : (
              <DeliverySummary totals={quote} legs={quote.legs} pending={isQuoting} />
            )}
          </section>

          <FormField label="Payment method">
            <select
              value={paymentMethod}
              onChange={(e) => setPaymentMethod(e.target.value)}
              className={inputClassName}
            >
              <option value="card">Card</option>
              <option value="mobile_money">Mobile money</option>
            </select>
          </FormField>

          {error && <ErrorText>{error}</ErrorText>}

          <Button type="submit" disabled={!canSubmit} fullWidth className="mt-2">
            {isSubmitting
              ? "Placing order…"
              : quote && !quoteError
                ? `Place order · ${formatCurrency(quote.total)}`
                : "Place order"}
          </Button>
        </form>
      </Card>
    </PageShell>
  );
}
