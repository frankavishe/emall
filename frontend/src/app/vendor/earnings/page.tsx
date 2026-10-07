"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import {
  errorMessage,
  getVendorEarnings,
  listVendorPayouts,
  updatePayoutDetails,
  type PayoutDetails,
  type PayoutNetwork,
  type VendorShopEarnings,
} from "@/lib/api-client";
import { formatCurrency } from "@/lib/currency";
import { PAYOUT_NETWORK_LABELS, formatRate, payoutStatusTone } from "@/lib/finance";
import { useApi, useRequireRole } from "@/lib/use-api";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Pill } from "@/components/ui/pill";
import { StatCard } from "@/components/ui/stat-card";
import { FormField, inputClassName } from "@/components/ui/form-field";
import { EmptyText, ErrorText, LoadingText } from "@/components/ui/status-text";
import { Pager } from "@/components/pager";

export default function VendorEarningsPage() {
  const allowed = useRequireRole("VENDOR");
  const earnings = useApi(getVendorEarnings, "earnings", allowed);
  const [page, setPage] = useState(1);
  const payouts = useApi(() => listVendorPayouts(page), String(page), allowed);

  if (!allowed) {
    return (
      <PageShell size="md" className="min-h-screen items-center justify-center">
        <LoadingText />
      </PageShell>
    );
  }

  return (
    <PageShell
      size="md"
      title="Earnings"
      description="Customers pay MangiMall. Once an order line is delivered, its earnings (after the mall's commission) become available and the mall sends them to your mobile-money account."
      actions={
        <Button asChild variant="secondary" size="sm">
          <Link href="/vendor/orders">Order lines</Link>
        </Button>
      }
    >
      {earnings.error && <ErrorText>{earnings.error}</ErrorText>}
      {earnings.isLoading && !earnings.data ? (
        <LoadingText>Loading earnings…</LoadingText>
      ) : !earnings.data || earnings.data.length === 0 ? (
        <EmptyText>You don&apos;t have a shop yet.</EmptyText>
      ) : (
        earnings.data.map((shop) => (
          <ShopEarnings key={shop.shop_id} shop={shop} onSaved={earnings.reload} />
        ))
      )}

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold text-text-primary">Payouts received</h2>
        {payouts.error && <ErrorText>{payouts.error}</ErrorText>}
        {!payouts.data || payouts.data.results.length === 0 ? (
          <p className="text-sm text-text-muted">No payouts yet.</p>
        ) : (
          <>
            <ul className="flex flex-col gap-2">
              {payouts.data.results.map((payout) => (
                <Card
                  as="li"
                  key={payout.id}
                  padding="sm"
                  className="flex flex-wrap items-center justify-between gap-2 text-sm"
                >
                  <div>
                    <p className="font-medium text-text-primary">
                      {formatCurrency(payout.amount)} &middot; {payout.shop.name}
                    </p>
                    <p className="text-text-muted">
                      {payout.reference} &middot;{" "}
                      {PAYOUT_NETWORK_LABELS[payout.network] ?? payout.network} {payout.phone}{" "}
                      &middot; {new Date(payout.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <Pill tone={payoutStatusTone(payout.status)}>{payout.status}</Pill>
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
      </section>
    </PageShell>
  );
}

function ShopEarnings({ shop, onSaved }: { shop: VendorShopEarnings; onSaved: () => void }) {
  const [isEditing, setIsEditing] = useState(!shop.has_payout_details);

  return (
    <section className="flex flex-col gap-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-lg font-semibold text-text-primary">{shop.shop_name}</h2>
        <span className="text-sm text-text-muted">
          Mall commission: {formatRate(shop.commission_rate)}
        </span>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard
          variant="hero"
          label="Available"
          value={formatCurrency(shop.available_balance)}
          trend={
            Number(shop.in_payout) > 0
              ? { text: `${formatCurrency(shop.in_payout)} on the way` }
              : undefined
          }
        />
        <StatCard label="Pending delivery" value={formatCurrency(shop.pending_earnings)} />
        <StatCard label="Paid to you" value={formatCurrency(shop.paid_out)} />
      </div>
      <p className="text-sm text-text-muted">
        Sales so far: {formatCurrency(shop.gross_sales)}, of which the mall&apos;s commission on
        delivered lines is {formatCurrency(shop.commission_earned)}.
      </p>

      <Card padding="sm" className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="font-semibold text-text-primary">Where we pay you</h3>
          {!isEditing && (
            <Button variant="ghost" size="sm" onClick={() => setIsEditing(true)}>
              Change
            </Button>
          )}
        </div>
        {isEditing ? (
          <PayoutDetailsForm
            shop={shop}
            onDone={() => {
              setIsEditing(false);
              onSaved();
            }}
            onCancel={shop.has_payout_details ? () => setIsEditing(false) : undefined}
          />
        ) : (
          <p className="text-sm text-text-primary">
            {PAYOUT_NETWORK_LABELS[shop.payout_network] ?? shop.payout_network} &middot;{" "}
            {shop.payout_phone} &middot; {shop.payout_account_name}
          </p>
        )}
      </Card>
    </section>
  );
}

function PayoutDetailsForm({
  shop,
  onDone,
  onCancel,
}: {
  shop: VendorShopEarnings;
  onDone: () => void;
  onCancel?: () => void;
}) {
  const [details, setDetails] = useState<PayoutDetails>({
    payout_network: shop.payout_network || "MPESA",
    payout_phone: shop.payout_phone,
    payout_account_name: shop.payout_account_name,
  });
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  async function save(e: FormEvent) {
    e.preventDefault();
    setIsSaving(true);
    setError(null);
    try {
      await updatePayoutDetails(shop.shop_id, details);
      onDone();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <form onSubmit={save} className="flex flex-col gap-3">
      {!shop.has_payout_details && (
        <p className="text-sm text-status-pending">
          Add your mobile-money details so the mall can pay you.
        </p>
      )}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <FormField label="Network">
          <select
            value={details.payout_network}
            onChange={(e) =>
              setDetails((prev) => ({ ...prev, payout_network: e.target.value as PayoutNetwork }))
            }
            className={inputClassName}
          >
            {Object.entries(PAYOUT_NETWORK_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </FormField>
        <FormField label="Phone number">
          <input
            type="tel"
            required
            placeholder="+255712345678"
            value={details.payout_phone}
            onChange={(e) => setDetails((prev) => ({ ...prev, payout_phone: e.target.value }))}
            className={inputClassName}
          />
        </FormField>
        <FormField label="Name on account">
          <input
            required
            value={details.payout_account_name}
            onChange={(e) =>
              setDetails((prev) => ({ ...prev, payout_account_name: e.target.value }))
            }
            className={inputClassName}
          />
        </FormField>
      </div>
      {error && <ErrorText>{error}</ErrorText>}
      <div className="flex gap-2">
        <Button type="submit" size="sm" disabled={isSaving}>
          {isSaving ? "Saving…" : "Save"}
        </Button>
        {onCancel && (
          <Button variant="ghost" size="sm" onClick={onCancel}>
            Cancel
          </Button>
        )}
      </div>
    </form>
  );
}
