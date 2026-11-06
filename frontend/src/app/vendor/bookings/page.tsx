"use client";

import { useState } from "react";
import {
  acceptBooking,
  declineBooking,
  errorMessage,
  listVendorBookings,
  type VendorBooking,
} from "@/lib/api-client";
import { formatCurrency } from "@/lib/currency";
import { formatMarketDateTime, formatMarketTime, MARKET_TIME_LABEL } from "@/lib/market-time";
import { useLiveRefresh } from "@/lib/realtime";
import { useApi, useRequireRole } from "@/lib/use-api";
import {
  BOOKING_STATUS_LABELS,
  BOOKING_STATUSES,
  BookingStatusPill,
} from "@/components/booking/booking-status";
import { Pager } from "@/components/pager";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { FormField, inputClassName } from "@/components/ui/form-field";
import { PageShell } from "@/components/ui/page-shell";
import { EmptyText, ErrorText, LoadingText } from "@/components/ui/status-text";

function RequestActions({
  booking,
  onDone,
  onError,
}: {
  booking: VendorBooking;
  onDone: () => void;
  onError: (message: string) => void;
}) {
  const [isDeclining, setIsDeclining] = useState(false);
  const [reason, setReason] = useState("");
  const [isPending, setIsPending] = useState(false);

  async function run(action: () => Promise<unknown>) {
    setIsPending(true);
    try {
      await action();
    } catch (err) {
      onError(errorMessage(err));
    } finally {
      setIsPending(false);
      onDone();
    }
  }

  if (isDeclining) {
    return (
      <form
        className="flex flex-col gap-2 border-t border-border pt-3"
        onSubmit={(event) => {
          event.preventDefault();
          void run(() => declineBooking(booking.id, reason));
        }}
      >
        <FormField label="Reason (optional, the customer sees this)">
          <input
            type="text"
            maxLength={1000}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            className={inputClassName}
          />
        </FormField>
        <div className="flex flex-wrap gap-2">
          <Button type="submit" variant="danger" size="sm" disabled={isPending}>
            {isPending ? "Declining…" : "Decline booking"}
          </Button>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            disabled={isPending}
            onClick={() => setIsDeclining(false)}
          >
            Back
          </Button>
        </div>
      </form>
    );
  }

  return (
    <div className="flex flex-wrap gap-2">
      <Button
        size="sm"
        disabled={isPending}
        onClick={() => void run(() => acceptBooking(booking.id))}
      >
        {isPending ? "Accepting…" : "Accept"}
      </Button>
      <Button
        variant="secondary"
        size="sm"
        disabled={isPending}
        onClick={() => setIsDeclining(true)}
      >
        Decline
      </Button>
    </div>
  );
}

export default function VendorBookingsPage() {
  const allowed = useRequireRole("VENDOR");
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  const { version } = useLiveRefresh(["booking.created", "booking.updated"], {
    enabled: allowed,
  });
  const bookings = useApi(
    () => listVendorBookings({ status, page }),
    `${status}|${page}|${version}`,
    allowed,
  );

  if (!allowed) {
    return (
      <PageShell size="md" className="min-h-screen items-center justify-center">
        <LoadingText />
      </PageShell>
    );
  }

  const results = bookings.data?.results ?? [];

  return (
    <PageShell
      size="md"
      title="Bookings"
      description={`Accept or decline requests before their deadline. Times are in ${MARKET_TIME_LABEL}.`}
    >
      <FormField label="Status">
        <select
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setPage(1);
          }}
          className={inputClassName}
        >
          <option value="">All</option>
          {BOOKING_STATUSES.map((value) => (
            <option key={value} value={value}>
              {BOOKING_STATUS_LABELS[value]}
            </option>
          ))}
        </select>
      </FormField>

      {actionError && <ErrorText>{actionError}</ErrorText>}
      {bookings.error && <ErrorText>{bookings.error}</ErrorText>}

      {bookings.isLoading && !bookings.data ? (
        <LoadingText>Loading bookings…</LoadingText>
      ) : results.length === 0 ? (
        bookings.error ? null : (
          <EmptyText>No bookings here yet.</EmptyText>
        )
      ) : (
        <ul className="flex flex-col gap-4">
          {results.map((booking) => (
            <Card as="li" key={booking.id} padding="sm" className="flex flex-col gap-3">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-medium text-text-primary">{booking.service.name}</p>
                  <p className="text-sm text-text-muted">
                    {formatMarketDateTime(booking.starts_at)} to {formatMarketTime(booking.ends_at)}{" "}
                    &middot; {booking.shop.name}
                  </p>
                  <p className="text-sm text-text-muted">
                    {booking.customer_name} &middot;{" "}
                    <a href={`tel:${booking.contact_phone}`} className="underline">
                      {booking.contact_phone}
                    </a>
                  </p>
                  <p className="text-sm text-text-muted">
                    {formatCurrency(booking.price)} &middot; You earn{" "}
                    {formatCurrency(booking.vendor_earning)}
                  </p>
                </div>
                <BookingStatusPill status={booking.status} />
              </div>

              {booking.customer_note && (
                <p className="whitespace-pre-line text-sm text-text-muted">
                  Note: {booking.customer_note}
                </p>
              )}
              {booking.status_reason && (
                <p className="text-sm text-text-muted">Reason: {booking.status_reason}</p>
              )}
              {booking.status === "AWAITING_PAYMENT" && booking.pay_by && (
                <p className="text-sm text-text-muted">
                  The customer has until {formatMarketDateTime(booking.pay_by)} to pay.
                </p>
              )}
              {booking.status === "REQUESTED" && (
                <>
                  <p className="text-sm font-medium text-text-primary">
                    Respond by {formatMarketDateTime(booking.respond_by)}
                  </p>
                  <RequestActions
                    booking={booking}
                    onDone={bookings.reload}
                    onError={setActionError}
                  />
                </>
              )}
            </Card>
          ))}
        </ul>
      )}

      <Pager
        previous={bookings.data?.previous ?? null}
        next={bookings.data?.next ?? null}
        onPrevious={() => setPage((current) => current - 1)}
        onNext={() => setPage((current) => current + 1)}
      />
    </PageShell>
  );
}
