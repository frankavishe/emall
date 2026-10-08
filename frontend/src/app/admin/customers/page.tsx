"use client";

import { useState } from "react";
import Link from "next/link";
import { listAdminCustomers } from "@/lib/api-client";
import { formatCurrency } from "@/lib/currency";
import { useApi, useRequireRole } from "@/lib/use-api";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Pill } from "@/components/ui/pill";
import { SegmentedToggle } from "@/components/ui/segmented-toggle";
import { ErrorText, LoadingText, EmptyText } from "@/components/ui/status-text";
import { FormField, inputClassName } from "@/components/ui/form-field";
import { Avatar } from "@/components/ui/avatar";
import { Pager } from "@/components/pager";
import { BlockToggle } from "@/components/admin/block-toggle";

type ActiveFilter = "active" | "blocked" | "all";

function filterToParam(filter: ActiveFilter): boolean | undefined {
  return filter === "all" ? undefined : filter === "active";
}

export default function AdminCustomersPage() {
  const allowed = useRequireRole("ADMINISTRATOR");
  const [filter, setFilter] = useState<ActiveFilter>("all");
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [notice, setNotice] = useState<string | null>(null);

  const customers = useApi(
    () => listAdminCustomers({ q: query, isActive: filterToParam(filter), page }),
    `${filter}|${query}|${page}`,
    allowed,
  );

  function handleSearch(event: React.FormEvent) {
    event.preventDefault();
    setPage(1);
    setQuery(search);
  }

  function handleFilter(next: ActiveFilter) {
    setPage(1);
    setFilter(next);
  }

  function handleChanged(message: string) {
    setNotice(message);
    customers.reload();
  }

  if (!allowed) {
    return (
      <PageShell size="md" className="min-h-screen items-center justify-center">
        <LoadingText />
      </PageShell>
    );
  }

  const results = customers.data?.results ?? [];

  return (
    <PageShell
      size="md"
      title="Customers"
      description="Shopper accounts, including vendors. Blocking stops someone from logging in and ends their current sessions."
    >
      <Card as="form" onSubmit={handleSearch} className="flex flex-wrap items-end gap-3">
        <div className="min-w-0 flex-1">
          <FormField label="Search">
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Name or email"
              className={inputClassName}
            />
          </FormField>
        </div>
        <Button type="submit">Search</Button>
      </Card>

      <SegmentedToggle
        options={[
          { value: "all", label: "ALL" },
          { value: "active", label: "ACTIVE" },
          { value: "blocked", label: "BLOCKED" },
        ]}
        value={filter}
        onChange={handleFilter}
        className="self-start"
      />

      {notice && <p className="text-sm font-medium text-status-delivered">{notice}</p>}
      {customers.error && <ErrorText>{customers.error}</ErrorText>}

      {customers.isLoading && !customers.data ? (
        <LoadingText>Loading customers…</LoadingText>
      ) : results.length === 0 ? (
        <EmptyText>No customers match.</EmptyText>
      ) : (
        <ul className="flex flex-col gap-4">
          {results.map((customer) => (
            <Card as="li" key={customer.id} padding="sm">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="flex min-w-0 items-start gap-3">
                  <Avatar name={customer.name} size="sm" />
                  <div className="min-w-0">
                    <Link
                      href={`/admin/customers/${customer.id}`}
                      className="font-medium text-text-primary hover:underline"
                    >
                      {customer.name}
                    </Link>
                    <p className="break-all text-sm text-text-muted">{customer.email}</p>
                    <p className="text-sm text-text-muted">
                      {customer.order_count} {customer.order_count === 1 ? "order" : "orders"}{" "}
                      &middot; {formatCurrency(customer.total_spent)} spent &middot; joined{" "}
                      {new Date(customer.date_joined).toLocaleDateString()}
                    </p>
                    <div className="mt-1 flex flex-wrap gap-1">
                      <Pill tone={customer.is_active ? "approved" : "cancelled"}>
                        {customer.is_active ? "ACTIVE" : "BLOCKED"}
                      </Pill>
                      {customer.is_vendor && <Pill tone="shipped">VENDOR</Pill>}
                      {!customer.is_email_verified && <Pill tone="pending">UNVERIFIED</Pill>}
                    </div>
                  </div>
                </div>
                <BlockToggle customer={customer} onChanged={handleChanged} />
              </div>
            </Card>
          ))}
        </ul>
      )}

      <Pager
        previous={customers.data?.previous ?? null}
        next={customers.data?.next ?? null}
        onPrevious={() => setPage((p) => Math.max(1, p - 1))}
        onNext={() => setPage((p) => p + 1)}
      />
    </PageShell>
  );
}
