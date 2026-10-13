"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { hasRole, useAuth } from "@/lib/auth-context";
import {
  ApiError,
  checkout,
  getDeliveryQuote,
  MOBILE_MONEY_PROVIDERS,
  orderPath,
  type DeliveryQuote,
  type LatLng,
  type MobileMoneyProvider,
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

// Tanzanian mobile number: 07XXXXXXXX / 06XXXXXXXX, optionally as +255 / 255. The server
// normalises and re-validates it.
const TZ_MOBILE = /^(?:\+?255|0)?[67]\d{8}$/;

function isValidMobile(value: string): boolean {
  return TZ_MOBILE.test(value.replace(/[\s-]/g, ""));
}

export default function CheckoutPage() {
  const router = useRouter();
  const { user, isLoading } = useAuth();
  const [shipping, setShipping] = useState<ShippingAddress>(EMPTY_SHIPPING);
  const [pin, setPin] = useState<LatLng | null>(null);
  const [quote, setQuote] = useState<DeliveryQuote | null>(null);
  const [quoteError, setQuoteError] = useState<string | null>(null);
  const [isQuoting, setIsQuoting] = useState(false);
  const [paymentMethod, setPaymentMethod] = useState("card");
  const [provider, setProvider] = useState<MobileMoneyProvider>("Mpesa");
  const [msisdn, setMsisdn] = useState("");
  const [msisdnError, setMsisdnError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [guestEmail, setGuestEmail] = useState("");
  const [guestEmailError, setGuestEmailError] = useState<string | null>(null);

  // Guests can check out too (guest checkout); only a signed-in non-customer is turned away.
  const isGuest = !user;
  const canShop = isGuest || hasRole(user, "CUSTOMER");

  useEffect(() => {
    if (!isLoading && !canShop) {
      router.replace("/login");
    }
  }, [isLoading, canShop, router]);

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
    const isMobileMoney = paymentMethod === "mobile_money";
    if (isMobileMoney && !isValidMobile(msisdn)) {
      setMsisdnError("Enter the mobile money number to charge, e.g. 0712345678.");
      return;
    }
    setError(null);
    setMsisdnError(null);
    setGuestEmailError(null);
    setFieldErrors({});
    setIsSubmitting(true);
    try {
      const order = await checkout(
        { ...shipping, ...pin },
        paymentMethod,
        isMobileMoney ? { msisdn, provider } : undefined,
        isGuest ? guestEmail.trim() : undefined,
      );
      const path = orderPath(order);
      router.push(order.status === "AWAITING_PAYMENT" ? `${path}/pay` : path);
    } catch (err) {
      if (err instanceof ApiError) {
        const body = err.body as {
          detail?: string;
          code?: string;
          order_id?: number;
          access_token?: string;
          shipping?: Record<string, string[]>;
          lines?: { reason: string }[];
          msisdn?: string[];
          provider?: string[];
          email?: string[];
        } | null;
        if (body?.code === "payment_pending" && (body.order_id || body.access_token)) {
          router.push(`${orderPath({ id: body.order_id, access_token: body.access_token })}/pay`);
          return;
        }
        if (body?.email) {
          setGuestEmailError(body.email[0]);
        } else if (body?.msisdn || body?.provider) {
          setMsisdnError(body.msisdn?.[0] ?? body.provider?.[0] ?? null);
        } else if (body?.shipping) {
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

  if (isLoading || !canShop) {
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
          {isGuest && (
            <div className="flex flex-col gap-2 rounded-control border border-border bg-card-muted p-4">
              <p className="text-sm text-text-muted">
                Checking out as a guest.{" "}
                <Link href="/login" className="font-medium text-brand-text underline">
                  Log in
                </Link>{" "}
                to keep your orders in your account.
              </p>
              <FormField label="Email">
                <input
                  type="email"
                  required
                  autoComplete="email"
                  value={guestEmail}
                  onChange={(e) => {
                    setGuestEmail(e.target.value);
                    setGuestEmailError(null);
                  }}
                  className={inputClassName}
                />
                <span className="text-xs text-text-muted">
                  We&apos;ll email your order confirmation and a private link to track it.
                </span>
                {guestEmailError && (
                  <span className="text-xs text-status-cancelled">{guestEmailError}</span>
                )}
              </FormField>
            </div>
          )}

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
              <option value="mobile_money">Mobile money (AzamPay)</option>
            </select>
          </FormField>

          {paymentMethod === "mobile_money" && (
            <div className="flex flex-col gap-4 rounded-control border border-border bg-card-muted p-4">
              <p className="text-sm text-text-muted">
                We&apos;ll send a payment prompt to this phone. Enter your mobile money PIN there to
                confirm the order.
              </p>
              <FormField label="Network">
                <select
                  value={provider}
                  onChange={(e) => setProvider(e.target.value as MobileMoneyProvider)}
                  className={inputClassName}
                >
                  {MOBILE_MONEY_PROVIDERS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </FormField>
              <FormField label="Mobile money number">
                <input
                  type="tel"
                  inputMode="tel"
                  autoComplete="tel"
                  placeholder="0712 345 678"
                  value={msisdn}
                  onChange={(e) => {
                    setMsisdn(e.target.value);
                    setMsisdnError(null);
                  }}
                  onBlur={() => {
                    if (msisdn && !isValidMobile(msisdn)) {
                      setMsisdnError("That doesn't look like a Tanzanian mobile number.");
                    }
                  }}
                  className={inputClassName}
                />
                {msisdnError && (
                  <span className="text-xs text-status-cancelled">{msisdnError}</span>
                )}
              </FormField>
            </div>
          )}

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
