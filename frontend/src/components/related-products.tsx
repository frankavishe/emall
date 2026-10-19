"use client";

import { useEffect, useState } from "react";
import { listRelatedProducts, type CatalogProduct } from "@/lib/api-client";
import { ProductCard } from "@/components/product-card";

/** "Related products" grid under the product page. Renders nothing when there are none or the
 * request fails — the product page stands on its own. */
export function RelatedProducts({ productId }: { productId: number }) {
  const [products, setProducts] = useState<CatalogProduct[]>([]);

  useEffect(() => {
    let cancelled = false;

    listRelatedProducts(productId)
      .then((result) => {
        if (!cancelled) setProducts(result);
      })
      .catch(() => {
        if (!cancelled) setProducts([]);
      });

    return () => {
      cancelled = true;
    };
  }, [productId]);

  if (products.length === 0) return null;

  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-lg font-semibold text-text-primary">Related products</h2>
      <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
        {products.map((product) => (
          <ProductCard key={product.id} product={product} />
        ))}
      </ul>
    </section>
  );
}
