"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { ApiError, checkout, type ShippingDetails } from "@/lib/api-client";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FormField, inputClassName } from "@/components/ui/form-field";
import { ErrorText, LoadingText } from "@/components/ui/status-text";

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
      <PageShell size="md" className="min-h-screen items-center justify-center">
        <LoadingText />
      </PageShell>
    );
  }

  return (
    <PageShell size="md">
      <Card>
        <h1 className="mb-6 text-2xl font-semibold text-text-primary">Checkout</h1>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {(Object.keys(EMPTY_SHIPPING) as (keyof ShippingDetails)[]).map((field) => (
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

          <Button type="submit" disabled={isSubmitting} fullWidth className="mt-2">
            {isSubmitting ? "Placing order…" : "Place order"}
          </Button>
        </form>
      </Card>
    </PageShell>
  );
}
