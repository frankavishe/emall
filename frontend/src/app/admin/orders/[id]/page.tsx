"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { getAdminOrder } from "@/lib/api-client";
import { formatCurrency } from "@/lib/currency";
import { formatRate, payoutStatusTone } from "@/lib/finance";
import { useApi, useRequireRole } from "@/lib/use-api";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Pill, statusToTone } from "@/components/ui/pill";
import { ErrorText, LoadingText } from "@/components/ui/status-text";

export default function AdminOrderDetailPage() {
  const params = useParams<{ id: string }>();
  const allowed = useRequireRole("ADMINISTRATOR");
  const order = useApi(() => getAdminOrder(params.id), params.id, allowed);

  if (!allowed || (order.isLoading && !order.data)) {
    return (
      <PageShell size="md" className="min-h-screen items-center justify-center">
        <LoadingText />
      </PageShell>
    );
  }

  const data = order.data;
  if (!data) {
    return (
      <PageShell size="md" title="Order">
        <ErrorText>{order.error ?? "Order not found."}</ErrorText>
      </PageShell>
    );
  }

  const vendorTotal = data.items.reduce((sum, line) => sum + Number(line.vendor_earning), 0);

  return (
    <PageShell
      size="md"
      title={`Order #${data.id}`}
      description={`Placed ${new Date(data.placed_at).toLocaleString()}`}
    >
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Card padding="sm" className="flex flex-col gap-1 text-sm">
          <h2 className="font-semibold text-text-primary">Customer</h2>
          <p className="text-text-primary">{data.customer.name}</p>
          <p className="text-text-muted">{data.customer.email}</p>
          <h3 className="mt-2 font-medium text-text-primary">Ship to</h3>
          <p className="text-text-muted">{data.recipient_name}</p>
          <p className="text-text-muted">{data.address_line}</p>
          <p className="text-text-muted">
            {data.city}, {data.region} {data.postal_code}
          </p>
          <p className="text-text-muted">{data.country}</p>
          <p className="text-text-muted">{data.phone}</p>
        </Card>

        <Card padding="sm" className="flex flex-col gap-2 text-sm">
          <h2 className="font-semibold text-text-primary">Payment</h2>
          {data.payment ? (
            <>
              <Row label="Paid to the mall">{formatCurrency(data.payment.amount)}</Row>
              <Row label="Method">{data.payment.method}</Row>
              <Row label="Status">{data.payment.status}</Row>
              <Row label="Reference">
                <span className="break-all">{data.payment.transaction_reference}</span>
              </Row>
            </>
          ) : (
            <p className="text-text-muted">No payment record.</p>
          )}
          <hr className="border-border" />
          <Row label="Mall commission">{formatCurrency(data.commission_total)}</Row>
          <Row label="Owed to shops">{formatCurrency(vendorTotal)}</Row>
        </Card>
      </div>

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold text-text-primary">Lines</h2>
        <ul className="flex flex-col gap-2">
          {data.items.map((line) => (
            <Card as="li" key={line.id} padding="sm" className="flex flex-col gap-2 text-sm">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <p className="font-medium text-text-primary">{line.product_name}</p>
                  <p className="text-text-muted">
                    <Link href={`/admin/shops/${line.shop.id}`} className="underline">
                      {line.shop.name}
                    </Link>{" "}
                    &middot; {line.quantity} &times; {formatCurrency(line.unit_price)} ={" "}
                    {formatCurrency(line.subtotal)}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Pill tone={statusToTone(line.status)}>{line.status}</Pill>
                  {line.payout && (
                    <Link href={`/admin/payouts/${line.payout.id}`}>
                      <Pill tone={payoutStatusTone(line.payout.status)}>
                        Payout {line.payout.status}
                      </Pill>
                    </Link>
                  )}
                </div>
              </div>
              <p className="text-text-muted">
                Commission {formatRate(line.commission_rate)}:{" "}
                {formatCurrency(line.commission_amount)} &middot; Shop gets{" "}
                <span className="font-medium text-text-primary">
                  {formatCurrency(line.vendor_earning)}
                </span>
              </p>
            </Card>
          ))}
        </ul>
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
