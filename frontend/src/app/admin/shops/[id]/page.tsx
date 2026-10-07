"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { getAdminShop, listAdminPayouts } from "@/lib/api-client";
import { formatCurrency } from "@/lib/currency";
import { PAYOUT_NETWORK_LABELS, formatRate, payoutStatusTone } from "@/lib/finance";
import { useApi, useRequireRole } from "@/lib/use-api";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Pill, statusToTone } from "@/components/ui/pill";
import { StatCard } from "@/components/ui/stat-card";
import { ErrorText, LoadingText } from "@/components/ui/status-text";
import { ShopLogo } from "@/components/shop-logo";

export default function AdminShopDetailPage() {
  const params = useParams<{ id: string }>();
  const allowed = useRequireRole("ADMINISTRATOR");
  const shop = useApi(() => getAdminShop(params.id), params.id, allowed);
  const payouts = useApi(() => listAdminPayouts({ shop: params.id }), params.id, allowed);

  if (!allowed || (shop.isLoading && !shop.data)) {
    return (
      <PageShell size="md" className="min-h-screen items-center justify-center">
        <LoadingText />
      </PageShell>
    );
  }

  const data = shop.data;
  if (!data) {
    return (
      <PageShell size="md" title="Shop">
        <ErrorText>{shop.error ?? "Shop not found."}</ErrorText>
      </PageShell>
    );
  }

  const { balance } = data;

  return (
    <PageShell
      size="lg"
      title={
        <span className="flex items-center gap-3">
          <ShopLogo url={data.logo_url} name={data.name} size="md" />
          {data.name}
        </span>
      }
      description={`Opened ${new Date(data.created_at).toLocaleDateString()}`}
      actions={
        <>
          <Pill tone={statusToTone(data.status)}>{data.status}</Pill>
          <Button asChild variant="secondary" size="sm">
            <Link href={`/admin/products?shop=${data.id}`}>Products</Link>
          </Button>
          <Button asChild variant="secondary" size="sm">
            <Link href="/admin/finance">Pay out</Link>
          </Button>
        </>
      }
    >
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard variant="hero" label="Gross sales" value={formatCurrency(balance.gross_sales)} />
        <StatCard
          label={`Mall commission (${formatRate(balance.commission_rate)}${balance.commission_rate_is_override ? ", custom" : ""})`}
          value={formatCurrency(balance.commission_earned)}
        />
        <StatCard label="Available to pay out" value={formatCurrency(balance.available_balance)} />
        <StatCard label="Paid out" value={formatCurrency(balance.paid_out)} />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Card padding="sm" className="flex flex-col gap-2 text-sm">
          <h2 className="font-semibold text-text-primary">Owner</h2>
          <Row label="Name">{data.owner.name}</Row>
          <Row label="Email">{data.owner.email}</Row>
          <Row label="Products">
            {data.product_count} ({data.published_product_count} published)
          </Row>
          {data.status_reason && <Row label="Status reason">{data.status_reason}</Row>}
        </Card>
        <Card padding="sm" className="flex flex-col gap-2 text-sm">
          <h2 className="font-semibold text-text-primary">Payout details</h2>
          {data.payout_network ? (
            <>
              <Row label="Network">
                {PAYOUT_NETWORK_LABELS[data.payout_network] ?? data.payout_network}
              </Row>
              <Row label="Phone">{data.payout_phone}</Row>
              <Row label="Account name">{data.payout_account_name}</Row>
            </>
          ) : (
            <p className="text-text-muted">
              Not set yet — the owner adds these on their Earnings page.
            </p>
          )}
          <Row label="Pending delivery">{formatCurrency(balance.pending_earnings)}</Row>
          {Number(balance.in_payout) > 0 && (
            <Row label="Payout in progress">{formatCurrency(balance.in_payout)}</Row>
          )}
        </Card>
      </div>

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold text-text-primary">Recent payouts</h2>
        {payouts.error && <ErrorText>{payouts.error}</ErrorText>}
        {!payouts.data || payouts.data.results.length === 0 ? (
          <p className="text-sm text-text-muted">No payouts yet.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {payouts.data.results.map((payout) => (
              <Card as="li" key={payout.id} padding="sm">
                <Link
                  href={`/admin/payouts/${payout.id}`}
                  className="flex flex-wrap items-center justify-between gap-2 text-sm"
                >
                  <span className="text-text-primary">
                    {payout.reference} &middot; {formatCurrency(payout.amount)}
                  </span>
                  <span className="flex items-center gap-2 text-text-muted">
                    {new Date(payout.created_at).toLocaleDateString()}
                    <Pill tone={payoutStatusTone(payout.status)}>{payout.status}</Pill>
                  </span>
                </Link>
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
