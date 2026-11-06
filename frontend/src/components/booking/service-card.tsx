import Link from "next/link";
import type { CatalogService } from "@/lib/api-client";
import { ShopLogo } from "@/components/shop-logo";
import { Card } from "@/components/ui/card";
import { formatCurrency } from "@/lib/currency";

/** `90` -> `1 hr 30 min`. */
export function formatDuration(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  if (hours === 0) return `${rest} min`;
  return rest === 0 ? `${hours} hr` : `${hours} hr ${rest} min`;
}

export function ServiceCard({ service }: { service: CatalogService }) {
  return (
    <Card as="li" padding="sm" className="shadow-card transition-shadow hover:shadow-card-hover">
      <Link href={`/services/${service.id}`} className="flex h-full flex-col gap-2">
        <p className="font-medium text-text-primary">{service.name}</p>
        <p className="flex items-center gap-1.5 text-sm text-text-muted">
          <ShopLogo url={service.shop.logo_url} name={service.shop.name} size="xs" />
          {service.shop.name}
        </p>
        {service.description && (
          <p className="line-clamp-2 text-sm text-text-muted">{service.description}</p>
        )}
        <p className="mt-auto text-sm font-medium text-text-primary">
          {formatCurrency(service.price)}
          <span className="font-normal text-text-muted">
            {" "}
            &middot; {formatDuration(service.duration_minutes)}
          </span>
        </p>
      </Link>
    </Card>
  );
}
