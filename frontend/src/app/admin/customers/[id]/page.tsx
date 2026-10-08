"use client";

import { useState, type ReactNode } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { getAdminCustomer } from "@/lib/api-client";
import { formatCurrency } from "@/lib/currency";
import { useApi, useRequireRole } from "@/lib/use-api";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Pill } from "@/components/ui/pill";
import { StatCard } from "@/components/ui/stat-card";
import { EmptyText, ErrorText, LoadingText } from "@/components/ui/status-text";
import { BlockToggle } from "@/components/admin/block-toggle";

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex justify-between gap-4">
      <span className="text-text-muted">{label}</span>
      <span className="min-w-0 break-all text-right text-text-primary">{children}</span>
    </div>
  );
}

export default function AdminCustomerDetailPage() {
  const params = useParams<{ id: string }>();
  const allowed = useRequireRole("ADMINISTRATOR");
  const customer = useApi(() => getAdminCustomer(params.id), params.id, allowed);
  const [notice, setNotice] = useState<string | null>(null);

  if (!allowed || (customer.isLoading && !customer.data)) {
    return (
      <PageShell size="md" className="min-h-screen items-center justify-center">
        <LoadingText />
      </PageShell>
    );
  }

  const data = customer.data;
  if (!data) {
    return (
      <PageShell size="md" title="Customer">
        <ErrorText>{customer.error ?? "Customer not found."}</ErrorText>
      </PageShell>
    );
  }

  return (
    <PageShell
      size="md"
      title={data.name}
      description={`Joined ${new Date(data.date_joined).toLocaleDateString()}`}
      actions={
        <BlockToggle
          customer={data}
          onChanged={(message) => {
            setNotice(message);
            customer.reload();
          }}
        />
      }
    >
      {notice && <p className="text-sm font-medium text-status-delivered">{notice}</p>}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard label="Orders" value={String(data.order_count)} />
        <StatCard label="Total spent" value={formatCurrency(data.total_spent)} />
        <StatCard label="Shops owned" value={String(data.shop_count)} />
      </div>

      <Card padding="sm" className="flex flex-col gap-2 text-sm">
        <h2 className="font-semibold text-text-primary">Account</h2>
        <Row label="Email">{data.email}</Row>
        <Row label="Status">
          <Pill tone={data.is_active ? "approved" : "cancelled"}>
            {data.is_active ? "ACTIVE" : "BLOCKED"}
          </Pill>
        </Row>
        <Row label="Email verified">{data.is_email_verified ? "Yes" : "No"}</Row>
        <Row label="Vendor">
          {data.is_vendor ? (
            <Link href="/admin/shops" className="underline">
              Yes &middot; view shops
            </Link>
          ) : (
            "No"
          )}
        </Row>
      </Card>

      <Card padding="sm" className="flex flex-col gap-3 text-sm">
        <h2 className="font-semibold text-text-primary">Recent orders</h2>
        {data.recent_orders.length === 0 ? (
          <EmptyText>No orders yet.</EmptyText>
        ) : (
          <ul className="flex flex-col divide-y divide-border">
            {data.recent_orders.map((order) => (
              <li key={order.id} className="flex items-center justify-between gap-3 py-2">
                <Link href={`/admin/orders/${order.id}`} className="font-medium underline">
                  Order #{order.id}
                </Link>
                <span className="text-text-muted">
                  {new Date(order.placed_at).toLocaleDateString()} &middot; {order.item_count}{" "}
                  {order.item_count === 1 ? "item" : "items"} &middot; {formatCurrency(order.total)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </PageShell>
  );
}
