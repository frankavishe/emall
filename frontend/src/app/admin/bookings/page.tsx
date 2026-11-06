"use client";

import { useState } from "react";
import Link from "next/link";
import { listAdminBookings } from "@/lib/api-client";
import { formatCurrency } from "@/lib/currency";
import { formatMarketDateTime, MARKET_TIME_LABEL } from "@/lib/market-time";
import { useLiveRefresh } from "@/lib/realtime";
import { useApi, useRequireRole } from "@/lib/use-api";
import {
  BOOKING_STATUS_LABELS,
  BOOKING_STATUSES,
  BookingStatusPill,
} from "@/components/booking/booking-status";
import { Pager } from "@/components/pager";
import { Card } from "@/components/ui/card";
import { FormField, inputClassName } from "@/components/ui/form-field";
import { PageShell } from "@/components/ui/page-shell";
import { EmptyText, ErrorText, LoadingText } from "@/components/ui/status-text";

export default function AdminBookingsPage() {
  const allowed = useRequireRole("ADMINISTRATOR");
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const { version } = useLiveRefresh(["booking.created", "booking.updated"], {
    enabled: allowed,
  });
  const bookings = useApi(
    () =>
      listAdminBookings({
        status,
        search: search.trim(),
        date_from: dateFrom,
        date_to: dateTo,
        page,
      }),
    [status, search.trim(), dateFrom, dateTo, page, version].join("|"),
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

  /** Any filter change starts again from the first page. */
  function filter(setter: (value: string) => void) {
    return (event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
      setter(event.target.value);
      setPage(1);
    };
  }

  return (
    <PageShell size="md" title="Bookings" description={`Times are in ${MARKET_TIME_LABEL}.`}>
      <Card padding="sm" className="grid gap-3 sm:grid-cols-2">
        <FormField label="Search">
          <input
            type="search"
            placeholder="Customer, shop or service"
            value={search}
            onChange={filter(setSearch)}
            className={inputClassName}
          />
        </FormField>
        <FormField label="Status">
          <select value={status} onChange={filter(setStatus)} className={inputClassName}>
            <option value="">All</option>
            {BOOKING_STATUSES.map((value) => (
              <option key={value} value={value}>
                {BOOKING_STATUS_LABELS[value]}
              </option>
            ))}
          </select>
        </FormField>
        <FormField label="Visit from">
          <input
            type="date"
            value={dateFrom}
            onChange={filter(setDateFrom)}
            className={inputClassName}
          />
        </FormField>
        <FormField label="Visit to">
          <input
            type="date"
            value={dateTo}
            onChange={filter(setDateTo)}
            className={inputClassName}
          />
        </FormField>
      </Card>

      {bookings.error && <ErrorText>{bookings.error}</ErrorText>}

      {bookings.isLoading && !bookings.data ? (
        <LoadingText>Loading bookings…</LoadingText>
      ) : results.length === 0 ? (
        bookings.error ? null : (
          <EmptyText>No bookings match.</EmptyText>
        )
      ) : (
        <ul className="flex flex-col gap-4">
          {results.map((booking) => (
            <Card as="li" key={booking.id} padding="sm">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <Link
                    href={`/admin/bookings/${booking.id}`}
                    className="font-medium text-text-primary hover:underline"
                  >
                    #{booking.id} &middot; {booking.service.name}
                  </Link>
                  <p className="text-sm text-text-muted">
                    {booking.shop.name} &middot; {booking.customer.name}
                  </p>
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
