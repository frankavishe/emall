"use client";

import { useState } from "react";
import Link from "next/link";
import {
  createShopPayout,
  errorMessage,
  getFinanceSettings,
  getFinanceSummary,
  listShopBalances,
  setShopCommissionRate,
  updateDefaultCommissionRate,
  type ShopBalance,
} from "@/lib/api-client";
import { formatCurrency } from "@/lib/currency";
import { formatRate, parseRateInput } from "@/lib/finance";
import { useApi, useRequireRole } from "@/lib/use-api";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Pill, statusToTone } from "@/components/ui/pill";
import { StatCard } from "@/components/ui/stat-card";
import { FormField, inputClassName } from "@/components/ui/form-field";
import { EmptyText, ErrorText, LoadingText } from "@/components/ui/status-text";
import { ShopLogo } from "@/components/shop-logo";
import { Pager } from "@/components/pager";

export default function AdminFinancePage() {
  const allowed = useRequireRole("ADMINISTRATOR");
  const [range, setRange] = useState({ from: "", to: "" });
  const [page, setPage] = useState(1);
  const [message, setMessage] = useState<{ tone: "ok" | "error"; text: string } | null>(null);

  const summary = useApi(() => getFinanceSummary(range), `${range.from}|${range.to}`, allowed);
  const balances = useApi(() => listShopBalances(page), String(page), allowed);

  function refresh() {
    summary.reload();
    balances.reload();
  }

  if (!allowed) {
    return (
      <PageShell size="md" className="min-h-screen items-center justify-center">
        <LoadingText />
      </PageShell>
    );
  }

  const figures = summary.data;

  return (
    <PageShell
      size="xl"
      title="Finance"
      description="Customers pay the mall. The mall keeps its commission and pays each shop the rest once an order line is delivered."
      actions={
        <>
          <Button asChild variant="secondary" size="sm">
            <Link href="/admin/transactions">Transactions</Link>
          </Button>
          <Button asChild variant="secondary" size="sm">
            <Link href="/admin/payouts">Payout history</Link>
          </Button>
        </>
      }
    >
      <div className="flex flex-wrap items-end gap-3">
        <FormField label="From">
          <input
            type="date"
            value={range.from}
            onChange={(e) => setRange((prev) => ({ ...prev, from: e.target.value }))}
            className={inputClassName}
          />
        </FormField>
        <FormField label="To">
          <input
            type="date"
            value={range.to}
            onChange={(e) => setRange((prev) => ({ ...prev, to: e.target.value }))}
            className={inputClassName}
          />
        </FormField>
        {(range.from || range.to) && (
          <Button variant="ghost" size="sm" onClick={() => setRange({ from: "", to: "" })}>
            All time
          </Button>
        )}
      </div>

      {summary.error && <ErrorText>{summary.error}</ErrorText>}
      {!figures ? (
        <LoadingText>Loading figures…</LoadingText>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <StatCard
            variant="hero"
            label="Customer payments (gross sales)"
            value={formatCurrency(figures.gross_sales)}
            trend={{ text: `${figures.order_count} orders` }}
          />
          <StatCard
            label="Mall commission earned"
            value={formatCurrency(figures.commission_earned)}
            trend={{ text: "delivered lines", tone: "positive" }}
          />
          <StatCard
            label="Commission on the way"
            value={formatCurrency(figures.commission_pending)}
            trend={{ text: "not delivered yet" }}
          />
          <StatCard
            label="Owed to shops now"
            value={formatCurrency(figures.available_balance)}
            trend={{ text: "ready to pay out" }}
          />
          <StatCard
            label="Shops' pending earnings"
            value={formatCurrency(figures.pending_earnings)}
            trend={{ text: "awaiting delivery" }}
          />
          <StatCard
            label="Paid out to shops"
            value={formatCurrency(figures.paid_out)}
            trend={
              Number(figures.in_payout) > 0
                ? { text: `${formatCurrency(figures.in_payout)} in progress` }
                : undefined
            }
          />
        </div>
      )}

      <DefaultRateCard onSaved={refresh} />

      <section className="flex flex-col gap-4">
        <h2 className="text-lg font-semibold text-text-primary">Shop balances</h2>
        {message && (
          <p
            className={
              message.tone === "ok"
                ? "text-sm text-status-delivered"
                : "text-sm text-status-cancelled"
            }
          >
            {message.text}
          </p>
        )}
        {balances.error && <ErrorText>{balances.error}</ErrorText>}
        {balances.isLoading && !balances.data ? (
          <LoadingText>Loading shops…</LoadingText>
        ) : !balances.data || balances.data.results.length === 0 ? (
          <EmptyText>No shops yet.</EmptyText>
        ) : (
          <>
            <ul className="flex flex-col gap-4">
              {balances.data.results.map((shop) => (
                <ShopBalanceRow
                  key={shop.id}
                  shop={shop}
                  onChanged={refresh}
                  onMessage={setMessage}
                />
              ))}
            </ul>
            <Pager
              previous={balances.data.previous}
              next={balances.data.next}
              onPrevious={() => setPage((p) => p - 1)}
              onNext={() => setPage((p) => p + 1)}
            />
          </>
        )}
      </section>
    </PageShell>
  );
}

function DefaultRateCard({ onSaved }: { onSaved: () => void }) {
  const settings = useApi(getFinanceSettings, "settings", true);
  const [draft, setDraft] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const current = settings.data?.default_commission_rate;
  const value = draft ?? (current ? String(Number(current)) : "");

  async function save() {
    const rate = parseRateInput(value);
    if (rate === null) {
      setError("Enter a percentage between 0 and 100.");
      return;
    }
    setIsSaving(true);
    setError(null);
    try {
      await updateDefaultCommissionRate(rate);
      setDraft(null);
      settings.reload();
      onSaved();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <Card padding="sm" className="flex flex-col gap-3">
      <div>
        <h2 className="font-semibold text-text-primary">Default commission</h2>
        <p className="text-sm text-text-muted">
          The mall&apos;s cut of every sale, unless a shop has its own rate. Changes apply to new
          orders only.
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <input
          inputMode="decimal"
          aria-label="Default commission percent"
          value={value}
          onChange={(e) => setDraft(e.target.value)}
          className={`w-24 ${inputClassName}`}
        />
        <span className="text-sm text-text-muted">%</span>
        <Button size="sm" disabled={isSaving || draft === null} onClick={save}>
          Save
        </Button>
      </div>
      {(error || settings.error) && <ErrorText>{error ?? settings.error}</ErrorText>}
    </Card>
  );
}

function ShopBalanceRow({
  shop,
  onChanged,
  onMessage,
}: {
  shop: ShopBalance;
  onChanged: () => void;
  onMessage: (message: { tone: "ok" | "error"; text: string }) => void;
}) {
  const [rateDraft, setRateDraft] = useState<string | null>(null);
  const [isConfirming, setIsConfirming] = useState(false);
  const [isBusy, setIsBusy] = useState(false);

  const available = Number(shop.available_balance);
  const canPay = available > 0 && shop.has_payout_details;

  async function saveRate(rate: string | null) {
    if (rate !== null && parseRateInput(rate) === null) {
      onMessage({ tone: "error", text: "Enter a percentage between 0 and 100." });
      return;
    }
    setIsBusy(true);
    try {
      await setShopCommissionRate(shop.id, rate === null ? null : parseRateInput(rate));
      setRateDraft(null);
      onMessage({ tone: "ok", text: `Commission for ${shop.name} updated.` });
      onChanged();
    } catch (err) {
      onMessage({ tone: "error", text: errorMessage(err) });
    } finally {
      setIsBusy(false);
    }
  }

  async function payOut() {
    setIsBusy(true);
    try {
      const payout = await createShopPayout(shop.id);
      onMessage(
        payout.status === "FAILED"
          ? {
              tone: "error",
              text: `Payout to ${shop.name} failed: ${payout.failure_reason || "unknown error"}. The balance is still available.`,
            }
          : {
              tone: "ok",
              text: `${formatCurrency(payout.amount)} sent to ${shop.name} (${payout.reference}, ${payout.status.toLowerCase()}).`,
            },
      );
      onChanged();
    } catch (err) {
      onMessage({ tone: "error", text: errorMessage(err) });
    } finally {
      setIsBusy(false);
      setIsConfirming(false);
    }
  }

  return (
    <Card as="li" padding="sm" className="flex flex-col gap-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <ShopLogo url={shop.logo_url} name={shop.name} size="md" />
          <div>
            <Link
              href={`/admin/shops/${shop.id}`}
              className="font-medium text-text-primary underline-offset-2 hover:underline"
            >
              {shop.name}
            </Link>
            <p className="text-sm text-text-muted">
              {shop.owner_name} &middot; {shop.owner_email}
            </p>
            <div className="mt-1 flex flex-wrap gap-2">
              <Pill tone={statusToTone(shop.status)}>{shop.status}</Pill>
              {!shop.has_payout_details && <Pill tone="pending">No payout details</Pill>}
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm text-text-muted">Commission</span>
          <input
            inputMode="decimal"
            aria-label={`Commission for ${shop.name}`}
            value={rateDraft ?? String(Number(shop.commission_rate))}
            onChange={(e) => setRateDraft(e.target.value)}
            className={`w-20 ${inputClassName}`}
          />
          <span className="text-sm text-text-muted">%</span>
          {rateDraft !== null && (
            <Button
              size="sm"
              variant="secondary"
              disabled={isBusy}
              onClick={() => saveRate(rateDraft)}
            >
              Save
            </Button>
          )}
          {shop.commission_rate_override !== null ? (
            <Button size="sm" variant="ghost" disabled={isBusy} onClick={() => saveRate(null)}>
              Use default
            </Button>
          ) : (
            <span className="text-xs text-text-muted">(mall default)</span>
          )}
        </div>
      </div>

      <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
        <Figure label="Gross sales" value={shop.gross_sales} />
        <Figure
          label={`Commission (${formatRate(shop.commission_rate)})`}
          value={shop.commission_earned}
        />
        <Figure label="Pending delivery" value={shop.pending_earnings} />
        <Figure label="Paid out" value={shop.paid_out} />
      </dl>

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-control bg-card-muted px-3 py-2">
        <div>
          <p className="text-xs text-text-muted">Available to pay out</p>
          <p className="text-lg font-semibold text-text-primary">
            {formatCurrency(shop.available_balance)}
          </p>
          {Number(shop.in_payout) > 0 && (
            <p className="text-xs text-text-muted">{formatCurrency(shop.in_payout)} in progress</p>
          )}
        </div>
        {isConfirming ? (
          <div className="flex items-center gap-2">
            <span className="text-sm text-text-primary">
              Send {formatCurrency(shop.available_balance)}?
            </span>
            <Button size="sm" disabled={isBusy} onClick={payOut}>
              {isBusy ? "Sending…" : "Confirm"}
            </Button>
            <Button
              size="sm"
              variant="ghost"
              disabled={isBusy}
              onClick={() => setIsConfirming(false)}
            >
              Cancel
            </Button>
          </div>
        ) : (
          <Button size="sm" disabled={!canPay || isBusy} onClick={() => setIsConfirming(true)}>
            Pay out
          </Button>
        )}
      </div>
    </Card>
  );
}

function Figure({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-text-muted">{label}</dt>
      <dd className="font-medium text-text-primary">{formatCurrency(value)}</dd>
    </div>
  );
}
