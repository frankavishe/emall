import Link from "next/link";
import type { CatalogProduct } from "@/lib/api-client";
import { StarRating } from "@/components/star-rating";

export function ProductCard({ product }: { product: CatalogProduct }) {
  return (
    <li className="rounded-md border border-black/15 p-4">
      <Link href={`/products/${product.id}`} className="flex flex-col gap-2">
        {product.thumbnail_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={product.thumbnail_url}
            alt={product.name}
            className="aspect-square w-full rounded-md object-cover"
          />
        ) : (
          <div className="flex aspect-square w-full items-center justify-center rounded-md bg-black/5 text-sm text-black/40">
            No image
          </div>
        )}
        <p className="font-medium">{product.name}</p>
        <p className="text-sm text-black/60">{product.shop_name}</p>
        <p className="text-sm font-medium">${product.price}</p>
        <p className="text-sm text-black/60">{product.in_stock ? "In stock" : "Out of stock"}</p>
        <StarRating rating={product.average_rating} reviewCount={product.review_count} />
      </Link>
    </li>
  );
}
