"use client";

import { useState } from "react";
import Link from "next/link";
import { listAdminTransactions } from "@/lib/api-client";
import { formatCurrency } from "@/lib/currency";
import { useApi, useRequireRole } from "@/lib/use-api";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Pill, statusToTone } from "@/components/ui/pill";
import { FormField, inputClassName } from "@/components/ui/form-field";
import { EmptyText, ErrorText, LoadingText } from "@/components/ui/status-text";
import { Pager } from "@/components/pager";

export default function AdminTransactionsPage() {
  const allowed = useRequireRole("ADMINISTRATOR");
  const [filters, setFilters] = useState({ from: "", to: "", search: "" });
  const [searchDraft, setSearchDraft] = useState("");
  const [page, setPage] = useState(1);
  const transactions = useApi(
    () => listAdminTransactions({ ...filters, page }),
    `${filters.from}|${filters.to}|${filters.search}|${page}`,
    allowed,
  );

  function updateFilters(next: Partial<typeof filters>) {
    setFilters((prev) => ({ ...prev, ...next }));
    setPage(1);
  }

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
      title="Transactions"
      description="Every payment customers have made to the mall, with the mall's commission on it."
    >
      <form
        className="flex flex-wrap items-end gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          updateFilters({ search: searchDraft.trim() });
        }}
      >
        <FormField label="Search">
          <input
            type="search"
            placeholder="Order #, reference, customer"
            value={searchDraft}
            onChange={(e) => setSearchDraft(e.target.value)}
            className={inputClassName}
          />
        </FormField>
        <FormField label="From">
          <input
            type="date"
            value={filters.from}
            onChange={(e) => updateFilters({ from: e.target.value })}
            className={inputClassName}
          />
        </FormField>
        <FormField label="To">
          <input
            type="date"
            value={filters.to}
            onChange={(e) => updateFilters({ to: e.target.value })}
            className={inputClassName}
          />
        </FormField>
        <Button type="submit" variant="secondary" size="sm">
          Search
        </Button>
      </form>

      {transactions.error && <ErrorText>{transactions.error}</ErrorText>}
      {transactions.isLoading && !transactions.data ? (
        <LoadingText>Loading transactions…</LoadingText>
      ) : !transactions.data || transactions.data.results.length === 0 ? (
        <EmptyText>No transactions match.</EmptyText>
      ) : (
        <>
          <p className="text-sm text-text-muted">{transactions.data.count} transactions</p>
          <ul className="flex flex-col gap-3">
            {transactions.data.results.map((tx) => (
              <Card as="li" key={tx.id} padding="sm">
                <Link
                  href={`/admin/orders/${tx.order_id}`}
                  className="flex flex-wrap items-start justify-between gap-3"
                >
                  <div>
                    <p className="font-medium text-text-primary">
                      Order #{tx.order_id} &middot; {tx.customer.name}
                    </p>
                    <p className="text-sm text-text-muted">
                      {tx.customer.email} &middot; {tx.method} &middot;{" "}
                      {new Date(tx.created_at).toLocaleString()}
                    </p>
                    <p className="break-all text-xs text-text-muted">
                      Ref {tx.transaction_reference} &middot; {tx.shop_count}{" "}
                      {tx.shop_count === 1 ? "shop" : "shops"}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-semibold text-text-primary">
                      {formatCurrency(tx.amount)}
                    </p>
                    <p className="text-sm text-status-delivered">
                      +{formatCurrency(tx.commission_total)} commission
                    </p>
                    <Pill tone={statusToTone(tx.status === "SUCCEEDED" ? "delivered" : tx.status)}>
                      {tx.status}
                    </Pill>
                  </div>
                </Link>
              </Card>
            ))}
          </ul>
          <Pager
            previous={transactions.data.previous}
            next={transactions.data.next}
            onPrevious={() => setPage((p) => p - 1)}
            onNext={() => setPage((p) => p + 1)}
          />
        </>
      )}
    </PageShell>
  );
}
