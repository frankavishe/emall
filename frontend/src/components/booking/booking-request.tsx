"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ApiError,
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

function BookingForm({ service, user }: { service: CatalogService; user: AuthUser }) {
  const router = useRouter();
  const [slot, setSlot] = useState<ServiceSlot | null>(null);
  const [phone, setPhone] = useState(user.phone);
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
      });
      router.push(`/bookings/${booking.id}`);
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

  if (!isLoading && user && hasRole(user, "CUSTOMER") && user.is_email_verified && !isOwnShop) {
    return <BookingForm key={user.id} service={service} user={user} />;
  }

  let prompt = null;
  if (!isLoading && !user) {
    prompt = (
      <p className="text-sm text-text-muted">
        <Link href="/login" className="font-medium text-text-primary underline">
          Sign in
        </Link>{" "}
        to book this service.
      </p>
    );
  } else if (user && isOwnShop) {
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
