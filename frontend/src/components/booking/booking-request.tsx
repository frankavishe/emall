"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ApiError,
  bookingPath,
  errorMessage,
  requestBooking,
  type CatalogService,
  type ServiceSlot,
} from "@/lib/api-client";
import { hasRole, useAuth, type AuthUser } from "@/lib/auth-context";
import { formatCurrency } from "@/lib/currency";
import { formatMarketDateTime, MARKET_TIME_LABEL } from "@/lib/market-time";
import { SlotPicker } from "@/components/booking/slot-picker";
import { Button } from "@/components/ui/button";
import { FormField, inputClassName } from "@/components/ui/form-field";
import { ErrorText } from "@/components/ui/status-text";

/** `user` is null for a guest, who books without an account by leaving a name and email. */
function BookingForm({ service, user }: { service: CatalogService; user: AuthUser | null }) {
  const router = useRouter();
  const isGuest = !user;
  const [slot, setSlot] = useState<ServiceSlot | null>(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState(user?.phone ?? "");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  function chooseSlot(next: ServiceSlot | null) {
    setSlot(next);
    setError(null);
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!slot) return;
    setError(null);
    setIsSubmitting(true);
    try {
      const booking = await requestBooking({
        service: service.id,
        starts_at: slot.starts_at,
        contact_phone: phone,
        customer_note: note,
        ...(isGuest ? { name: name.trim(), email: email.trim() } : {}),
      });
      router.push(bookingPath(booking));
    } catch (err) {
      setError(errorMessage(err));
      // Someone else may have just taken this time, so show what's really open now.
      if (err instanceof ApiError && err.status === 400) {
        const body = err.body;
        if (body && typeof body === "object" && "detail" in body) {
          setSlot(null);
          setRefreshKey((key) => key + 1);
        }
      }
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <SlotPicker
        serviceId={service.id}
        selected={slot}
        onSelect={chooseSlot}
        refreshKey={refreshKey}
      />

      {error && <ErrorText>{error}</ErrorText>}

      {slot && (
        <form onSubmit={handleSubmit} className="flex flex-col gap-4 border-t border-border pt-4">
          <p className="text-sm font-medium text-text-primary">
            {formatMarketDateTime(slot.starts_at)} ({MARKET_TIME_LABEL}) &middot;{" "}
            {formatCurrency(service.price)}
          </p>
          {isGuest && (
            <>
              <FormField label="Your name">
                <input
                  type="text"
                  required
                  autoComplete="name"
                  maxLength={255}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className={inputClassName}
                />
              </FormField>
              <FormField label="Email">
                <input
                  type="email"
                  required
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className={inputClassName}
                />
              </FormField>
            </>
          )}
          <FormField label="Contact phone">
            <input
              type="tel"
              required
              autoComplete="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+255712345678"
              className={inputClassName}
            />
          </FormField>
          <FormField label="Note for the provider (optional)">
            <textarea
              rows={3}
              maxLength={1000}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              className={inputClassName}
            />
          </FormField>
          <p className="text-sm text-text-muted">
            You won&apos;t pay anything yet. The provider responds first, and you pay only if they
            accept.
          </p>
          {isGuest && (
            <p className="text-sm text-text-muted">
              No account needed: we&apos;ll email you a private link to follow your booking. Have an
              account?{" "}
              <Link href="/login" className="font-medium text-text-primary underline">
                Sign in
              </Link>
              .
            </p>
          )}
          <Button type="submit" disabled={isSubmitting} className="self-start">
            {isSubmitting ? "Sending…" : "Request this time"}
          </Button>
        </form>
      )}
    </div>
  );
}

/** Open times for a service, plus whatever this visitor needs in order to book one. */
export function BookingRequest({ service }: { service: CatalogService }) {
  const { user, isLoading } = useAuth();
  const isOwnShop = !!user?.shops?.some((shop) => String(shop.id) === String(service.shop.id));

  if (!isLoading && !user) {
    return <BookingForm key="guest" service={service} user={null} />;
  }
  if (!isLoading && user && hasRole(user, "CUSTOMER") && user.is_email_verified && !isOwnShop) {
    return <BookingForm key={user.id} service={service} user={user} />;
  }

  let prompt = null;
  if (user && isOwnShop) {
    prompt = <p className="text-sm text-text-muted">This service is in your own shop.</p>;
  } else if (user && hasRole(user, "CUSTOMER") && !user.is_email_verified) {
    prompt = (
      <p className="text-sm text-text-muted">
        <Link href="/verify-email" className="font-medium text-text-primary underline">
          Verify your email
        </Link>{" "}
        to book this service.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <SlotPicker serviceId={service.id} />
      {prompt}
    </div>
  );
}
