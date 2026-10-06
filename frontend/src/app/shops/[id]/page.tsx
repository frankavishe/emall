"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ApiError,
  getPublicShop,
  listProducts,
  type CatalogProduct,
  type CatalogShop,
} from "@/lib/api-client";
import { shopThemeStyle } from "@/lib/shop-theme";
import { ProductCard } from "@/components/product-card";
import { ShopLogo } from "@/components/shop-logo";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { EmptyText, ErrorText, LoadingText } from "@/components/ui/status-text";

/** Public storefront for one approved shop, rendered in the shop's own colors. */
export default function ShopPage() {
  const params = useParams<{ id: string }>();
  const [shop, setShop] = useState<CatalogShop | null>(null);
  const [products, setProducts] = useState<CatalogProduct[]>([]);
  const [productCount, setProductCount] = useState(0);
  const [nextPage, setNextPage] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadShop() {
      setIsLoading(true);
      setError(null);
      try {
        const [shopResult, productResult] = await Promise.all([
          getPublicShop(params.id),
          listProducts({ shop: params.id }),
        ]);
        if (cancelled) return;
        setShop(shopResult);
        setProducts(productResult.results);
        setProductCount(productResult.count);
        setNextPage(productResult.next ? 2 : null);
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof ApiError && err.status === 404
              ? "This shop doesn't exist or isn't open yet."
              : "Something went wrong. Please try again.",
          );
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    void loadShop();
    return () => {
      cancelled = true;
    };
  }, [params.id]);

  async function loadMore() {
    if (!nextPage) return;
    setIsLoadingMore(true);
    try {
      const result = await listProducts({ shop: params.id, page: nextPage });
      setProducts((current) => [...current, ...result.results]);
      setNextPage(result.next ? nextPage + 1 : null);
    } catch {
      // non-fatal — the button stays so the customer can retry
    } finally {
      setIsLoadingMore(false);
    }
  }

  if (isLoading) {
    return (
      <PageShell size="xl" className="min-h-screen items-center justify-center">
        <LoadingText />
      </PageShell>
    );
  }

  if (error || !shop) {
    return (
      <PageShell size="xl" className="min-h-screen items-center justify-center">
        <ErrorText>{error ?? "Shop not found."}</ErrorText>
        <Link href="/products" className="text-sm font-medium text-text-primary underline">
          Browse all products
        </Link>
      </PageShell>
    );
  }

  return (
    // `contents` keeps the page layout untouched; the wrapper only scopes the theme variables.
    <div className="contents" style={shopThemeStyle(shop)}>
      <PageShell size="xl">
        <Card variant="hero" className="relative overflow-hidden">
          <div
            aria-hidden
            className="absolute -right-16 -top-16 h-48 w-48 rounded-full bg-teal-400/30"
          />
          <div className="relative flex items-center gap-4">
            <ShopLogo
              url={shop.logo_url}
              name={shop.name}
              size="lg"
              className="ring-2 ring-on-primary/40"
            />
            <div>
              <h1 className="text-2xl font-semibold">{shop.name}</h1>
              <p className="text-sm opacity-80">
                {productCount} {productCount === 1 ? "product" : "products"}
              </p>
            </div>
          </div>
          <div aria-hidden className="relative mt-4 h-1 w-16 rounded-pill bg-teal-400" />
        </Card>

        {products.length === 0 ? (
          <EmptyText>This shop has no products yet.</EmptyText>
        ) : (
          <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
            {products.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </ul>
        )}

        {nextPage && (
          <Button
            variant="secondary"
            className="self-center"
            disabled={isLoadingMore}
            onClick={() => void loadMore()}
          >
            {isLoadingMore ? "Loading…" : "Load more"}
          </Button>
        )}
      </PageShell>
    </div>
  );
}
