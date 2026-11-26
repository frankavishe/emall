import Link from "next/link";
import type { CatalogShopListItem } from "@/lib/api-client";
import { shopThemeStyle } from "@/lib/shop-theme";
import { ShopLogo } from "@/components/shop-logo";
import { Card } from "@/components/ui/card";

/** A merchants-directory card, drawn in the shop's own colors. */
export function ShopCard({ shop }: { shop: CatalogShopListItem }) {
  return (
    <li style={shopThemeStyle(shop)}>
      <Link href={`/shops/${shop.id}`} className="block h-full">
        <Card className="flex h-full flex-col gap-3 transition-shadow hover:shadow-md">
          <div className="flex items-center gap-3">
            <ShopLogo url={shop.logo_url} name={shop.name} size="md" />
            <div className="min-w-0">
              <h2 className="truncate font-semibold text-text-primary">{shop.name}</h2>
              <p className="text-xs text-text-muted">
                {shop.business_type === "SERVICES"
                  ? `${shop.service_count} ${shop.service_count === 1 ? "service" : "services"}`
                  : `${shop.product_count} ${shop.product_count === 1 ? "product" : "products"}`}
              </p>
            </div>
          </div>
          {shop.description && (
            <p className="line-clamp-3 text-sm text-text-muted">{shop.description}</p>
          )}
          <span className="mt-auto h-1 w-12 rounded-pill bg-teal-400" aria-hidden />
          <span className="text-sm font-medium text-text-primary">Visit shop →</span>
        </Card>
      </Link>
    </li>
  );
}
