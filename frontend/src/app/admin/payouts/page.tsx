"use client";

import { useState } from "react";
import Link from "next/link";
import { listAdminPayouts } from "@/lib/api-client";
import { formatCurrency } from "@/lib/currency";
import { PAYOUT_NETWORK_LABELS, payoutStatusTone } from "@/lib/finance";
import { useApi, useRequireRole } from "@/lib/use-api";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Pill } from "@/components/ui/pill";
import { SegmentedToggle } from "@/components/ui/segmented-toggle";
import { EmptyText, ErrorText, LoadingText } from "@/components/ui/status-text";
import { Pager } from "@/components/pager";

type StatusFilter = "" | "SUCCEEDED" | "PROCESSING" | "FAILED";

export default function AdminPayoutsPage() {
  const allowed = useRequireRole("ADMINISTRATOR");
  const [status, setStatus] = useState<StatusFilter>("");
  const [page, setPage] = useState(1);
  const payouts = useApi(() => listAdminPayouts({ page, status }), `${page}|${status}`, allowed);

  if (!allowed) {
    return (
      <PageShell size="md" className="min-h-screen items-center justify-center">
        <LoadingText />
      </PageShell>
    );
  }

  return (
    <PageShell size="md" title="Payouts" description="Money the mall has sent to shop owners.">
      <SegmentedToggle
        options={[
          { value: "", label: "ALL" },
          { value: "SUCCEEDED", label: "SUCCEEDED" },
          { value: "PROCESSING", label: "PROCESSING" },
          { value: "FAILED", label: "FAILED" },
        ]}
        value={status}
        onChange={(value) => {
          setStatus(value);
          setPage(1);
        }}
        className="self-start"
      />

      {payouts.error && <ErrorText>{payouts.error}</ErrorText>}
      {payouts.isLoading && !payouts.data ? (
        <LoadingText>Loading payouts…</LoadingText>
      ) : !payouts.data || payouts.data.results.length === 0 ? (
        <EmptyText>No payouts yet. Pay shops from the Finance page.</EmptyText>
      ) : (
        <>
          <ul className="flex flex-col gap-3">
            {payouts.data.results.map((payout) => (
              <Card as="li" key={payout.id} padding="sm">
                <Link
                  href={`/admin/payouts/${payout.id}`}
                  className="flex flex-wrap items-start justify-between gap-3"
                >
                  <div>
                    <p className="font-medium text-text-primary">
                      {payout.shop.name} &middot; {formatCurrency(payout.amount)}
                    </p>
                    <p className="text-sm text-text-muted">
                      {payout.reference} &middot;{" "}
                      {PAYOUT_NETWORK_LABELS[payout.network] ?? payout.network} {payout.phone}
                      &middot; {new Date(payout.created_at).toLocaleString()}
                    </p>
                    {payout.failure_reason && (
                      <p className="text-sm text-status-cancelled">{payout.failure_reason}</p>
                    )}
                  </div>
                  <Pill tone={payoutStatusTone(payout.status)}>{payout.status}</Pill>
                </Link>
              </Card>
            ))}
          </ul>
          <Pager
            previous={payouts.data.previous}
            next={payouts.data.next}
            onPrevious={() => setPage((p) => p - 1)}
            onNext={() => setPage((p) => p + 1)}
          />
        </>
      )}
    </PageShell>
  );
}
