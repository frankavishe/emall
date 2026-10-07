"use client";

import { useState, type ReactNode } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { errorMessage, getAdminPayout, retryPayout } from "@/lib/api-client";
import { formatCurrency } from "@/lib/currency";
import { PAYOUT_NETWORK_LABELS, formatRate, payoutStatusTone } from "@/lib/finance";
import { useApi, useRequireRole } from "@/lib/use-api";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Pill } from "@/components/ui/pill";
import { ErrorText, LoadingText } from "@/components/ui/status-text";

export default function AdminPayoutDetailPage() {
  const params = useParams<{ id: string }>();
  const allowed = useRequireRole("ADMINISTRATOR");
  const payout = useApi(() => getAdminPayout(params.id), params.id, allowed);
  const [retryError, setRetryError] = useState<string | null>(null);
  const [isRetrying, setIsRetrying] = useState(false);

  async function handleRetry() {
    setIsRetrying(true);
    setRetryError(null);
    try {
      await retryPayout(params.id);
      payout.reload();
    } catch (err) {
      setRetryError(errorMessage(err));
    } finally {
      setIsRetrying(false);
    }
  }

  if (!allowed || (payout.isLoading && !payout.data)) {
    return (
      <PageShell size="md" className="min-h-screen items-center justify-center">
        <LoadingText />
      </PageShell>
    );
  }

  const data = payout.data;
  if (!data) {
    return (
      <PageShell size="md" title="Payout">
        <ErrorText>{payout.error ?? "Payout not found."}</ErrorText>
      </PageShell>
    );
  }

  return (
    <PageShell
      size="md"
      title={`${data.reference} · ${formatCurrency(data.amount)}`}
      description={
        <>
          To{" "}
          <Link href={`/admin/shops/${data.shop.id}`} className="underline">
            {data.shop.name}
          </Link>
        </>
      }
      actions={<Pill tone={payoutStatusTone(data.status)}>{data.status}</Pill>}
    >
      <Card padding="sm" className="flex flex-col gap-2 text-sm">
        <Row label="Sent to">
          {PAYOUT_NETWORK_LABELS[data.network] ?? data.network} &middot; {data.phone} &middot;{" "}
          {data.account_name}
        </Row>
        <Row label="Provider reference">{data.provider_reference ?? "—"}</Row>
        <Row label="Started">
          {new Date(data.created_at).toLocaleString()}
          {data.created_by_name ? ` by ${data.created_by_name}` : ""}
        </Row>
        <Row label="Completed">
          {data.completed_at ? new Date(data.completed_at).toLocaleString() : "—"}
        </Row>
        {data.failure_reason && (
          <Row label="Failure">
            <span className="text-status-cancelled">{data.failure_reason}</span>
          </Row>
        )}
      </Card>

      {data.status === "FAILED" && (
        <div className="flex flex-col gap-2">
          <p className="text-sm text-text-muted">
            The lines from this payout went back to the shop&apos;s available balance. Retrying uses
            the shop&apos;s current payout details and everything it has available now.
          </p>
          <Button className="self-start" disabled={isRetrying} onClick={handleRetry}>
            {isRetrying ? "Retrying…" : "Retry payout"}
          </Button>
          {retryError && <ErrorText>{retryError}</ErrorText>}
        </div>
      )}

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold text-text-primary">Order lines paid</h2>
        {data.items.length === 0 ? (
          <p className="text-sm text-text-muted">No lines attached.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {data.items.map((line) => (
              <Card
                as="li"
                key={line.id}
                padding="sm"
                className="flex flex-wrap justify-between gap-2 text-sm"
              >
                <div>
                  <p className="font-medium text-text-primary">{line.product_name}</p>
                  <p className="text-text-muted">
                    <Link href={`/admin/orders/${line.order_id}`} className="underline">
                      Order #{line.order_id}
                    </Link>{" "}
                    &middot; {line.quantity} &times; {formatCurrency(line.unit_price)}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-text-muted">
                    {formatCurrency(line.subtotal)} − {formatCurrency(line.commission_amount)} (
                    {formatRate(line.commission_rate)})
                  </p>
                  <p className="font-medium text-text-primary">
                    {formatCurrency(line.vendor_earning)}
                  </p>
                </div>
              </Card>
            ))}
          </ul>
        )}
      </section>
    </PageShell>
  );
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-wrap justify-between gap-2">
      <span className="text-text-muted">{label}</span>
      <span className="text-text-primary">{children}</span>
    </div>
  );
}
