import Link from "next/link";
import type { CatalogProduct } from "@/lib/api-client";
import { StarRating } from "@/components/star-rating";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/cn";
import { formatCurrency } from "@/lib/currency";

export function ProductCard({ product }: { product: CatalogProduct }) {
  return (
    <Card as="li" padding="sm" className="shadow-card transition-shadow hover:shadow-card-hover">
      <Link href={`/products/${product.id}`} className="flex flex-col gap-2">
        {product.thumbnail_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={product.thumbnail_url}
            alt={product.name}
            className="aspect-square w-full rounded-control object-cover"
          />
        ) : (
          <div
            className={cn(
              "flex aspect-square w-full items-center justify-center rounded-control bg-card-muted text-sm text-text-muted",
            )}
          >
            No image
          </div>
        )}
        <p className="font-medium text-text-primary">{product.name}</p>
        <p className="text-sm text-text-muted">{product.shop_name}</p>
        <p className="text-sm font-medium text-text-primary">{formatCurrency(product.price)}</p>
        <p className="text-sm text-text-muted">{product.in_stock ? "In stock" : "Out of stock"}</p>
        <StarRating rating={product.average_rating} reviewCount={product.review_count} />
      </Link>
    </Card>
  );
}
