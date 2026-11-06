"use client";

import { useState } from "react";
import Link from "next/link";
import { listBookings } from "@/lib/api-client";
import { formatCurrency } from "@/lib/currency";
import { formatMarketDateTime, MARKET_TIME_LABEL } from "@/lib/market-time";
import { useLiveRefresh } from "@/lib/realtime";
import { useApi, useRequireRole } from "@/lib/use-api";
import { BookingStatusPill } from "@/components/booking/booking-status";
import { Pager } from "@/components/pager";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PageShell } from "@/components/ui/page-shell";
import { EmptyText, ErrorText, LoadingText } from "@/components/ui/status-text";

export default function BookingsPage() {
  const allowed = useRequireRole("CUSTOMER");
  const [page, setPage] = useState(1);
  const { version } = useLiveRefresh(["booking.updated"], { enabled: allowed });
  const bookings = useApi(() => listBookings({ page }), `${page}|${version}`, allowed);

  if (!allowed) {
    return (
      <PageShell size="md" className="min-h-screen items-center justify-center">
        <LoadingText />
      </PageShell>
    );
  }

  const results = bookings.data?.results ?? [];

  return (
    <PageShell size="md" title="My bookings" description={`Times are in ${MARKET_TIME_LABEL}.`}>
      {bookings.error && <ErrorText>{bookings.error}</ErrorText>}

      {bookings.isLoading && !bookings.data ? (
        <LoadingText>Loading bookings…</LoadingText>
      ) : results.length === 0 ? (
        bookings.error ? null : (
          <div className="flex flex-col items-start gap-3">
            <EmptyText>You haven&apos;t booked anything yet.</EmptyText>
            <Button asChild variant="secondary">
              <Link href="/services">Browse services</Link>
            </Button>
          </div>
        )
      ) : (
        <ul className="flex flex-col gap-4">
          {results.map((booking) => (
            <Card as="li" key={booking.id} padding="sm">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <Link
                    href={`/bookings/${booking.id}`}
                    className="font-medium text-text-primary hover:underline"
                  >
                    {booking.service.name}
                  </Link>
                  <p className="text-sm text-text-muted">{booking.shop.name}</p>
                  <p className="text-sm text-text-muted">
                    {formatMarketDateTime(booking.starts_at)} &middot;{" "}
                    {formatCurrency(booking.price)}
                  </p>
                </div>
                <BookingStatusPill status={booking.status} />
              </div>
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
