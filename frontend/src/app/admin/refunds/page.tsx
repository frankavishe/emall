"use client";

import { useState } from "react";
import Link from "next/link";
import {
  ApiError,
  errorMessage,
  listAdminRefunds,
  markRefundPaid,
  paymentMethodLabel,
  type AdminRefund,
} from "@/lib/api-client";
import { hasAdminPermission, useAuth } from "@/lib/auth-context";
import { formatCurrency } from "@/lib/currency";
import { formatMarketDateTime } from "@/lib/market-time";
import { useLiveRefresh } from "@/lib/realtime";
import { useApi, useRequireRole } from "@/lib/use-api";
import { REFUND_REASON_LABELS } from "@/components/booking/booking-status";
import { Pager } from "@/components/pager";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { FormField, inputClassName } from "@/components/ui/form-field";
import { PageShell } from "@/components/ui/page-shell";
import { Pill, statusToTone } from "@/components/ui/pill";
import { EmptyText, ErrorText, LoadingText } from "@/components/ui/status-text";

/** Money owed back to customers for bookings. Administrators send it by hand, then record the
 * transfer reference here. */
export default function AdminRefundsPage() {
  const allowed = useRequireRole("ADMINISTRATOR");
  const { user } = useAuth();
  const canPay = hasAdminPermission(user, "finance.manage");
  const [status, setStatus] = useState("DUE");
  const [page, setPage] = useState(1);
  const { version } = useLiveRefresh(["refund.updated"], { enabled: allowed });
  const refunds = useApi(
    () => listAdminRefunds({ status, page }),
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

  return (
    <PageShell
      size="lg"
      title="Refunds"
      description="Money owed back to customers for cancelled or late-paid bookings. Send it, then record the transfer here."
    >
      <div className="flex flex-wrap items-end gap-3">
        <FormField label="Status">
          <select
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setPage(1);
            }}
            className={inputClassName}
          >
            <option value="DUE">Due</option>
            <option value="PAID">Paid</option>
            <option value="">All</option>
          </select>
        </FormField>
      </div>

      {refunds.error && <ErrorText>{refunds.error}</ErrorText>}
      {refunds.isLoading && !refunds.data ? (
        <LoadingText>Loading refunds…</LoadingText>
      ) : !refunds.data || refunds.data.results.length === 0 ? (
        <EmptyText>{status === "DUE" ? "Nothing is owed back." : "No refunds match."}</EmptyText>
      ) : (
        <>
          <p className="text-sm text-text-muted">
            {refunds.data.count} {refunds.data.count === 1 ? "refund" : "refunds"}
          </p>
          <ul className="flex flex-col gap-3">
            {refunds.data.results.map((refund) => (
              <RefundRow key={refund.id} refund={refund} canPay={canPay} onPaid={refunds.reload} />
            ))}
          </ul>
          <Pager
            previous={refunds.data.previous}
            next={refunds.data.next}
            onPrevious={() => setPage((p) => p - 1)}
            onNext={() => setPage((p) => p + 1)}
          />
        </>
      )}
    </PageShell>
  );
}

function RefundRow({
  refund,
  canPay,
  onPaid,
}: {
  refund: AdminRefund;
  canPay: boolean;
  onPaid: () => void;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [reference, setReference] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  async function markPaid() {
    setIsSaving(true);
    setError(null);
    try {
      await markRefundPaid(refund.id, reference.trim());
      setIsOpen(false);
      onPaid();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        // Someone else recorded it first: show the current state.
        onPaid();
      }
      setError(errorMessage(err, "Couldn't save. Please try again."));
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <Card as="li" padding="sm" className="flex flex-col gap-2 text-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-medium text-text-primary">
            {formatCurrency(refund.amount)} &middot; {REFUND_REASON_LABELS[refund.reason]}
          </p>
          <p className="text-text-muted">
            <Link href={`/admin/bookings/${refund.booking_id}`} className="underline">
              Booking #{refund.booking_id}
            </Link>{" "}
            &middot; {refund.service} at {refund.shop}
          </p>
          <p className="text-text-muted">
            {refund.customer_name} ({refund.customer_email}) &middot; {refund.contact_phone}
          </p>
          <p className="break-all text-xs text-text-muted">
            Paid by {paymentMethodLabel(refund.payment_method)}
            {refund.payment_msisdn && <> from {refund.payment_msisdn}</>}
            {refund.payment_reference && <> &middot; Txn {refund.payment_reference}</>} &middot;
            Owed since {formatMarketDateTime(refund.created_at)}
          </p>
          {refund.note && <p className="text-text-muted">Note: {refund.note}</p>}
          {refund.status === "PAID" && (
            <p className="break-all text-xs text-text-muted">
              Sent {refund.paid_at && formatMarketDateTime(refund.paid_at)}
              {refund.paid_by_email && <> by {refund.paid_by_email}</>} &middot; Ref{" "}
              {refund.paid_reference}
            </p>
          )}
        </div>
        <Pill tone={statusToTone(refund.status)}>{refund.status === "PAID" ? "Paid" : "Due"}</Pill>
      </div>

      {refund.status === "DUE" && canPay && (
        <div className="flex flex-col gap-2 border-t border-border pt-2">
          {!isOpen ? (
            <div>
              <Button size="sm" onClick={() => setIsOpen(true)}>
                Mark paid
              </Button>
            </div>
          ) : (
            <>
              <FormField label="Transfer reference">
                <input
                  type="text"
                  maxLength={128}
                  value={reference}
                  placeholder="e.g. the M-Pesa transaction ID"
                  onChange={(e) => setReference(e.target.value)}
                  className={inputClassName}
                />
              </FormField>
              <div className="flex flex-wrap gap-2">
                <Button
                  size="sm"
                  disabled={isSaving || !reference.trim()}
                  onClick={() => void markPaid()}
                >
                  {isSaving ? "Saving…" : `Record ${formatCurrency(refund.amount)} sent`}
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={isSaving}
                  onClick={() => setIsOpen(false)}
                >
                  Back
                </Button>
              </div>
            </>
          )}
          {error && <ErrorText>{error}</ErrorText>}
        </div>
      )}
    </Card>
  );
}
