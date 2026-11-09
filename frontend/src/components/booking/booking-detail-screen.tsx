"use client";

import { useState, type ReactNode } from "react";
import Link from "next/link";
import { errorMessage, type BookingDetail } from "@/lib/api-client";
import { formatCurrency } from "@/lib/currency";
import { formatMarketDateTime, formatMarketTime, MARKET_TIME_LABEL } from "@/lib/market-time";
import { BookingHistory, BookingStatusPill } from "@/components/booking/booking-status";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { PageShell } from "@/components/ui/page-shell";
import { ErrorText, LoadingText } from "@/components/ui/status-text";

function statusMessage(booking: BookingDetail): string | null {
  switch (booking.status) {
    case "REQUESTED":
      return `This time is held for you while ${booking.shop.name} decides. They have until ${formatMarketDateTime(booking.respond_by)} to respond. You won't pay anything unless they accept.`;
    case "AWAITING_PAYMENT":
      return `${booking.shop.name} accepted your booking. It's held until ${formatMarketDateTime(booking.pay_by ?? booking.respond_by)}, the deadline to pay. Online payment for bookings isn't available yet.`;
    case "DECLINED":
      return "The provider declined this booking, and you haven't been charged.";
    case "EXPIRED":
      return "This booking expired before it was confirmed, and you haven't been charged.";
    case "CANCELLED":
      return "This booking was cancelled.";
    default:
      return null;
  }
}

type BookingState = {
  data: BookingDetail | null;
  isLoading: boolean;
  error: string | null;
  errorStatus: number | null;
  reload: () => void;
};

/** One booking as its customer sees it: a signed-in customer's (by id) or a guest's (by their
 * private link). The caller loads it and says how to cancel it. */
export function BookingDetailScreen({
  booking,
  ready = true,
  cancel,
  back,
  notice,
}: {
  booking: BookingState;
  ready?: boolean;
  cancel: () => Promise<unknown>;
  back: { href: string; label: string };
  notice?: ReactNode;
}) {
  const [isConfirming, setIsConfirming] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  async function handleCancel() {
    setIsCancelling(true);
    setActionError(null);
    try {
      await cancel();
      setIsConfirming(false);
    } catch (err) {
      setActionError(errorMessage(err));
    } finally {
      setIsCancelling(false);
      booking.reload();
    }
  }

  if (!ready || (booking.isLoading && !booking.data)) {
    return (
      <PageShell size="md" className="min-h-screen items-center justify-center">
        <LoadingText />
      </PageShell>
    );
  }

  if (!booking.data) {
    const isMissing = booking.errorStatus === 404;
    return (
      <ErrorState
        code={isMissing ? "404" : undefined}
        title={isMissing ? "Booking not found" : "Couldn't load this booking"}
        description={
          isMissing
            ? "This booking doesn't exist or isn't yours."
            : (booking.error ?? "Something went wrong. Please try again.")
        }
        actions={
          <Button asChild>
            <Link href={back.href}>{back.label}</Link>
          </Button>
        }
      />
    );
  }

  const data = booking.data;
  const canCancel = data.status === "REQUESTED" || data.status === "AWAITING_PAYMENT";
  const message = statusMessage(data);

  return (
    <PageShell size="md">
      <Card className="flex flex-col gap-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h1 className="text-2xl font-semibold text-text-primary">{data.service.name}</h1>
            <Link
              href={`/shops/${data.shop.id}`}
              className="text-sm font-medium text-text-muted hover:underline"
            >
              {data.shop.name}
            </Link>
          </div>
          <BookingStatusPill status={data.status} />
        </div>

        <p className="text-sm text-text-primary">
          {formatMarketDateTime(data.starts_at)} to {formatMarketTime(data.ends_at)} (
          {MARKET_TIME_LABEL})
        </p>
        <p className="text-lg font-semibold text-text-primary">{formatCurrency(data.price)}</p>
        {message && <p className="text-sm text-text-muted">{message}</p>}
        {data.status_reason && (
          <p className="text-sm text-text-muted">Reason: {data.status_reason}</p>
        )}
        <p className="text-sm text-text-muted">Contact phone: {data.contact_phone}</p>
        {data.customer_note && (
          <p className="whitespace-pre-line text-sm text-text-muted">
            Your note: {data.customer_note}
          </p>
        )}
        {notice}

        {actionError && <ErrorText>{actionError}</ErrorText>}

        {canCancel &&
          (isConfirming ? (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm text-text-primary">Cancel this booking?</span>
              <Button variant="danger" size="sm" disabled={isCancelling} onClick={handleCancel}>
                {isCancelling ? "Cancelling…" : "Yes, cancel it"}
              </Button>
              <Button
                variant="secondary"
                size="sm"
                disabled={isCancelling}
                onClick={() => setIsConfirming(false)}
              >
                Keep it
              </Button>
            </div>
          ) : (
            <Button
              variant="secondary"
              size="sm"
              className="self-start"
              onClick={() => setIsConfirming(true)}
            >
              Cancel booking
            </Button>
          ))}
      </Card>

      <Card className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold text-text-primary">History</h2>
        <BookingHistory events={data.history} />
      </Card>
    </PageShell>
  );
}
