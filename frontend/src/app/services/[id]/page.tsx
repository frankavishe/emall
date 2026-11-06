"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { getService } from "@/lib/api-client";
import { formatCurrency } from "@/lib/currency";
import { shopThemeStyle } from "@/lib/shop-theme";
import { useApi } from "@/lib/use-api";
import { formatDuration } from "@/components/booking/service-card";
import { SlotPicker } from "@/components/booking/slot-picker";
import { ShopLogo } from "@/components/shop-logo";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { PageShell } from "@/components/ui/page-shell";
import { LoadingText } from "@/components/ui/status-text";

export default function ServiceDetailPage() {
  const params = useParams<{ id: string }>();
  const service = useApi(() => getService(params.id), params.id, true);

  if (service.isLoading && !service.data) {
    return (
      <PageShell size="md" className="min-h-screen items-center justify-center">
        <LoadingText />
      </PageShell>
    );
  }

  if (!service.data) {
    const isMissing = service.errorStatus === 404;
    return (
      <ErrorState
        code={isMissing ? "404" : undefined}
        title={isMissing ? "Service not found" : "Couldn't load this service"}
        description={
          isMissing
            ? "This service doesn't exist or isn't available right now."
            : (service.error ?? "Something went wrong. Please try again.")
        }
        actions={
          <Button asChild>
            <Link href="/services">Browse services</Link>
          </Button>
        }
      />
    );
  }

  const { shop, ...details } = service.data;

  return (
    <div className="contents" style={shopThemeStyle(shop)}>
      <PageShell size="md">
        <Card className="flex flex-col gap-3">
          <p className="text-xs font-medium uppercase tracking-wide text-text-muted">
            {details.category}
          </p>
          <h1 className="text-2xl font-semibold text-text-primary">{details.name}</h1>
          <Link
            href={`/shops/${shop.id}`}
            className="flex items-center gap-2 text-sm font-medium text-text-muted hover:underline"
          >
            <ShopLogo url={shop.logo_url} name={shop.name} size="xs" />
            {shop.name}
          </Link>
          <p className="text-lg font-semibold text-text-primary">
            {formatCurrency(details.price)}
            <span className="text-sm font-normal text-text-muted">
              {" "}
              &middot; {formatDuration(details.duration_minutes)}
            </span>
          </p>
          {details.description && (
            <p className="whitespace-pre-line text-sm text-text-muted">{details.description}</p>
          )}
        </Card>

        <Card className="flex flex-col gap-4">
          <h2 className="text-lg font-semibold text-text-primary">When it&apos;s open</h2>
          <SlotPicker serviceId={details.id} />
        </Card>
      </PageShell>
    </div>
  );
}
