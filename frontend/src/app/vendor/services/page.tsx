"use client";

import { useState } from "react";
import Link from "next/link";
import {
  archiveVendorService,
  errorMessage,
  listVendorServices,
  setVendorServicePublished,
  type VendorService,
} from "@/lib/api-client";
import { formatCurrency } from "@/lib/currency";
import { useApi, useRequireRole } from "@/lib/use-api";
import { formatDuration } from "@/components/booking/service-card";
import { Pager } from "@/components/pager";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PageShell } from "@/components/ui/page-shell";
import { Pill } from "@/components/ui/pill";
import { EmptyText, ErrorText, LoadingText } from "@/components/ui/status-text";

export default function VendorServicesPage() {
  const allowed = useRequireRole("VENDOR");
  const [page, setPage] = useState(1);
  const services = useApi(() => listVendorServices(page), String(page), allowed);
  const [actionError, setActionError] = useState<string | null>(null);
  const [pendingId, setPendingId] = useState<number | null>(null);

  async function run(service: VendorService, action: () => Promise<unknown>) {
    setPendingId(service.id);
    setActionError(null);
    try {
      await action();
      services.reload();
    } catch (err) {
      setActionError(errorMessage(err));
    } finally {
      setPendingId(null);
    }
  }

  if (!allowed) {
    return (
      <PageShell size="md" className="min-h-screen items-center justify-center">
        <LoadingText />
      </PageShell>
    );
  }

  const results = services.data?.results ?? [];

  return (
    <PageShell
      size="md"
      title="My services"
      actions={
        <>
          <Button asChild variant="secondary">
            <Link href="/vendor/schedule">Hours</Link>
          </Button>
          <Button asChild>
            <Link href="/vendor/services/new">New service</Link>
          </Button>
        </>
      }
    >
      {actionError && <ErrorText>{actionError}</ErrorText>}
      {services.error && <ErrorText>{services.error}</ErrorText>}

      {services.isLoading && !services.data ? (
        <LoadingText>Loading services…</LoadingText>
      ) : results.length === 0 ? (
        services.error ? null : (
          <EmptyText>You haven&apos;t created any services yet.</EmptyText>
        )
      ) : (
        <ul className="flex flex-col gap-4">
          {results.map((service) => (
            <Card as="li" key={service.id} padding="sm">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-medium text-text-primary">{service.name}</p>
                  <p className="text-sm text-text-muted">
                    {service.shop.name} &middot; {service.category_name}
                  </p>
                  <p className="mt-1 text-sm text-text-muted">
                    {formatCurrency(service.price)} &middot;{" "}
                    {formatDuration(service.duration_minutes)}
                  </p>
                  <div className="mt-2">
                    <Pill tone={service.is_published ? "delivered" : "neutral"}>
                      {service.is_published ? "Published" : "Draft"}
                    </Pill>
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <Button variant="secondary" size="sm" asChild>
                    <Link href={`/vendor/services/${service.id}/edit`}>Edit</Link>
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={pendingId === service.id}
                    onClick={() =>
                      run(service, () =>
                        setVendorServicePublished(service.id, !service.is_published),
                      )
                    }
                  >
                    {service.is_published ? "Unpublish" : "Publish"}
                  </Button>
                  <Button
                    variant="danger"
                    size="sm"
                    disabled={pendingId === service.id}
                    onClick={() => run(service, () => archiveVendorService(service.id))}
                  >
                    Archive
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </ul>
      )}

      <Pager
        previous={services.data?.previous ?? null}
        next={services.data?.next ?? null}
        onPrevious={() => setPage((current) => current - 1)}
        onNext={() => setPage((current) => current + 1)}
      />
    </PageShell>
  );
}
