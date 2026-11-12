"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  adminCancelBooking,
  errorMessage,
  getAdminBooking,
  paymentMethodLabel,
  settleBookingPayment,
  type AdminBookingDetail,
  type BookingPayment,
} from "@/lib/api-client";
import { hasAdminPermission, useAuth } from "@/lib/auth-context";
import { formatCurrency } from "@/lib/currency";
import { formatMarketDateTime, formatMarketTime, MARKET_TIME_LABEL } from "@/lib/market-time";
import { useLiveRefresh } from "@/lib/realtime";
import { useApi, useRequireRole } from "@/lib/use-api";
import {
  BookingHistory,
  BookingStatusPill,
  REFUND_REASON_LABELS,
} from "@/components/booking/booking-status";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { FormField, inputClassName } from "@/components/ui/form-field";
import { PageShell } from "@/components/ui/page-shell";
import { Pill, statusToTone } from "@/components/ui/pill";
import { EmptyText, ErrorText, LoadingText } from "@/components/ui/status-text";

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
  const { user } = useAuth();
  const { version } = useLiveRefresh(["booking.updated", "refund.updated"], { enabled: allowed });
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
            {data.customer.is_guest && " · Guest, no account"}
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

      <PaymentsCard
        booking={data}
        canSettle={hasAdminPermission(user, "finance.manage")}
        onChanged={booking.reload}
      />

      {hasAdminPermission(user, "bookings.manage") && (
        <CancelCard booking={data} onChanged={booking.reload} />
      )}

      <Card className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold text-text-primary">History</h2>
        <BookingHistory events={data.history} />
      </Card>
    </PageShell>
  );
}

function PaymentLine({ payment }: { payment: BookingPayment }) {
  return (
    <div className="flex flex-col gap-1 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-medium text-text-primary">
          {paymentMethodLabel(payment.method)} &middot; {formatCurrency(payment.amount)}
        </span>
        <Pill tone={statusToTone(payment.status)}>{payment.status}</Pill>
      </div>
      <p className="break-all text-text-muted">
        {formatMarketDateTime(payment.created_at)}
        {payment.msisdn && <> &middot; {payment.msisdn}</>}
        {payment.payer_reference && <> &middot; Txn {payment.payer_reference}</>}
      </p>
      {payment.failure_reason && <p className="text-text-muted">{payment.failure_reason}</p>}
    </div>
  );
}

/** Every payment attempt and anything owed back, plus Lipa Namba settlement. */
function PaymentsCard({
  booking,
  canSettle,
  onChanged,
}: {
  booking: AdminBookingDetail;
  canSettle: boolean;
  onChanged: () => void;
}) {
  const pendingLipa = booking.payments.find(
    (payment) => payment.method === "lipa_namba" && payment.status === "PENDING",
  );

  return (
    <Card className="flex flex-col gap-3">
      <h2 className="text-lg font-semibold text-text-primary">Payments</h2>
      {booking.payments.length === 0 ? (
        <EmptyText>No payment attempts yet.</EmptyText>
      ) : (
        <ul className="flex flex-col gap-3">
          {booking.payments.map((payment) => (
            <li key={payment.id}>
              <PaymentLine payment={payment} />
            </li>
          ))}
        </ul>
      )}
      {pendingLipa && canSettle && (
        <LipaSettlement booking={booking} payment={pendingLipa} onSettled={onChanged} />
      )}

      {booking.refunds.length > 0 && (
        <>
          <h3 className="font-semibold text-text-primary">Owed back</h3>
          <ul className="flex flex-col gap-2 text-sm">
            {booking.refunds.map((refund) => (
              <li key={refund.id} className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-text-primary">
                  {formatCurrency(refund.amount)} &middot; {REFUND_REASON_LABELS[refund.reason]}
                </span>
                <Pill tone={statusToTone(refund.status)}>
                  {refund.status === "PAID" && refund.paid_at
                    ? `Paid ${formatMarketDateTime(refund.paid_at)}`
                    : "Due"}
                </Pill>
              </li>
            ))}
          </ul>
          <Link href="/admin/refunds" className="text-sm underline">
            All refunds
          </Link>
        </>
      )}
    </Card>
  );
}

function LipaSettlement({
  booking,
  payment,
  onSettled,
}: {
  booking: AdminBookingDetail;
  payment: BookingPayment;
  onSettled: () => void;
}) {
  const [mode, setMode] = useState<"idle" | "confirm" | "reject">("idle");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  async function settle(action: "confirm" | "reject") {
    setIsSaving(true);
    setError(null);
    try {
      await settleBookingPayment(booking.id, action, action === "reject" ? reason.trim() : "");
      setMode("idle");
      onSettled();
    } catch (err) {
      setError(errorMessage(err, "Couldn't save. Please try again."));
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-2 border-t border-border pt-3 text-sm">
      {mode === "idle" && (
        <>
          <p className="text-text-muted">
            Check transaction ID {payment.payer_reference || "(none given)"} and{" "}
            {formatCurrency(payment.amount)} on the till statement before confirming.
          </p>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" onClick={() => setMode("confirm")}>
              Confirm payment
            </Button>
            <Button size="sm" variant="secondary" onClick={() => setMode("reject")}>
              Reject
            </Button>
          </div>
        </>
      )}

      {mode === "confirm" && (
        <>
          <p className="text-text-primary">
            Mark {formatCurrency(payment.amount)} as received for booking #{booking.id}? If the time
            is no longer held or the visit has started, it is recorded as owed back instead.
          </p>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" disabled={isSaving} onClick={() => settle("confirm")}>
              {isSaving ? "Saving…" : "Yes, received"}
            </Button>
            <Button size="sm" variant="ghost" disabled={isSaving} onClick={() => setMode("idle")}>
              Back
            </Button>
          </div>
        </>
      )}

      {mode === "reject" && (
        <>
          <p className="text-text-primary">
            The customer can try paying again until the payment deadline.
          </p>
          <FormField label="Reason (shown to the customer)">
            <input
              type="text"
              maxLength={255}
              value={reason}
              placeholder="No matching transaction found"
              onChange={(e) => setReason(e.target.value)}
              className={inputClassName}
            />
          </FormField>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="danger" disabled={isSaving} onClick={() => settle("reject")}>
              {isSaving ? "Saving…" : "Reject payment"}
            </Button>
            <Button size="sm" variant="ghost" disabled={isSaving} onClick={() => setMode("idle")}>
              Back
            </Button>
          </div>
        </>
      )}

      {error && <ErrorText>{error}</ErrorText>}
    </div>
  );
}

const CANCELLABLE = ["REQUESTED", "AWAITING_PAYMENT", "CONFIRMED"];

/** Cancel any active booking. A paid one is owed back the refund amount (default: all of it). */
function CancelCard({
  booking,
  onChanged,
}: {
  booking: AdminBookingDetail;
  onChanged: () => void;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [refundAmount, setRefundAmount] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  if (!CANCELLABLE.includes(booking.status)) return null;
  const paid = booking.payments.find((payment) => payment.status === "SUCCEEDED");
  const paying = booking.payments.some((payment) => payment.status === "PENDING");

  async function cancel() {
    setIsSaving(true);
    setError(null);
    try {
      await adminCancelBooking(booking.id, reason.trim(), refundAmount.trim() || undefined);
      setIsOpen(false);
      onChanged();
    } catch (err) {
      setError(errorMessage(err, "Couldn't cancel. Please try again."));
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <Card className="flex flex-col gap-3 text-sm">
      <h2 className="text-lg font-semibold text-text-primary">Cancel booking</h2>
      {paying ? (
        <p className="text-text-muted">
          A payment is in progress. Wait for it to finish before cancelling.
        </p>
      ) : !isOpen ? (
        <div>
          <Button size="sm" variant="secondary" onClick={() => setIsOpen(true)}>
            Cancel booking
          </Button>
        </div>
      ) : (
        <>
          <FormField label="Reason (required, the customer and provider see this)">
            <input
              type="text"
              maxLength={255}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className={inputClassName}
            />
          </FormField>
          {paid && (
            <FormField label={`Refund (up to ${formatCurrency(paid.amount)}; blank refunds all)`}>
              <input
                type="number"
                inputMode="decimal"
                min="0.01"
                step="0.01"
                max={paid.amount}
                value={refundAmount}
                placeholder={paid.amount}
                onChange={(e) => setRefundAmount(e.target.value)}
                className={inputClassName}
              />
            </FormField>
          )}
          <div className="flex flex-wrap gap-2">
            <Button
              size="sm"
              variant="danger"
              disabled={isSaving || !reason.trim()}
              onClick={() => void cancel()}
            >
              {isSaving ? "Cancelling…" : "Cancel booking"}
            </Button>
            <Button size="sm" variant="ghost" disabled={isSaving} onClick={() => setIsOpen(false)}>
              Back
            </Button>
          </div>
        </>
      )}
      {error && <ErrorText>{error}</ErrorText>}
    </Card>
  );
}
