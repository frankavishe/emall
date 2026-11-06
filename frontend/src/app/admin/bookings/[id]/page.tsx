"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { getAdminBooking } from "@/lib/api-client";
import { formatCurrency } from "@/lib/currency";
import { formatMarketDateTime, formatMarketTime, MARKET_TIME_LABEL } from "@/lib/market-time";
import { useLiveRefresh } from "@/lib/realtime";
import { useApi, useRequireRole } from "@/lib/use-api";
import { BookingHistory, BookingStatusPill } from "@/components/booking/booking-status";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { PageShell } from "@/components/ui/page-shell";
import { LoadingText } from "@/components/ui/status-text";

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-wrap justify-between gap-x-4 gap-y-1 text-sm">
      <dt className="text-text-muted">{label}</dt>
      <dd className="min-w-0 text-text-primary">{children}</dd>
    </div>
  );
}

export default function AdminBookingDetailPage() {
  const params = useParams<{ id: string }>();
  const allowed = useRequireRole("ADMINISTRATOR");
  const { version } = useLiveRefresh(["booking.updated"], { enabled: allowed });
  const booking = useApi(() => getAdminBooking(params.id), `${params.id}|${version}`, allowed);

  if (!allowed || (booking.isLoading && !booking.data)) {
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
        description={booking.error ?? "Something went wrong. Please try again."}
        actions={
          <Button asChild>
            <Link href="/admin/bookings">All bookings</Link>
          </Button>
        }
      />
    );
  }

  const data = booking.data;

  return (
    <PageShell size="md">
      <Card className="flex flex-col gap-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-sm text-text-muted">Booking #{data.id}</p>
            <h1 className="text-2xl font-semibold text-text-primary">{data.service.name}</h1>
          </div>
          <BookingStatusPill status={data.status} />
        </div>

        <dl className="flex flex-col gap-2">
          <Row label="Shop">{data.shop.name}</Row>
          <Row label="Customer">
            {data.customer.name} ({data.customer.email})
          </Row>
          <Row label="Contact phone">{data.contact_phone}</Row>
          <Row label={`Visit (${MARKET_TIME_LABEL})`}>
            {formatMarketDateTime(data.starts_at)} to {formatMarketTime(data.ends_at)}
          </Row>
          <Row label="Respond by">{formatMarketDateTime(data.respond_by)}</Row>
          {data.pay_by && <Row label="Pay by">{formatMarketDateTime(data.pay_by)}</Row>}
          <Row label="Price">{formatCurrency(data.price)}</Row>
          <Row label={`Commission (${data.commission_rate}%)`}>
            {formatCurrency(data.commission_amount)}
          </Row>
          <Row label="Provider earns">{formatCurrency(data.vendor_earning)}</Row>
          {data.customer_note && <Row label="Customer note">{data.customer_note}</Row>}
          {data.status_reason && <Row label="Reason">{data.status_reason}</Row>}
        </dl>
      </Card>

      <Card className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold text-text-primary">History</h2>
        <BookingHistory events={data.history} />
      </Card>
    </PageShell>
  );
}
