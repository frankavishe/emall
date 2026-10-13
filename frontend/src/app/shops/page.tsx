"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listPublicShops, type CatalogShopListItem } from "@/lib/api-client";
import { shopThemeStyle } from "@/lib/shop-theme";
import { ShopLogo } from "@/components/shop-logo";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { EmptyText, ErrorText, LoadingText } from "@/components/ui/status-text";

/** Public merchants directory: every approved shop, each card in the shop's own colors. */
export default function ShopsPage() {
  const [shops, setShops] = useState<CatalogShopListItem[]>([]);
  const [count, setCount] = useState(0);
  const [nextPage, setNextPage] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listPublicShops()
      .then((result) => {
        if (cancelled) return;
        setShops(result.results);
        setCount(result.count);
        setNextPage(result.next ? 2 : null);
      })
      .catch(() => {
        if (!cancelled) setError("Something went wrong. Please try again.");
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function loadMore() {
    if (!nextPage) return;
    setIsLoadingMore(true);
    try {
      const result = await listPublicShops(nextPage);
      setShops((current) => [...current, ...result.results]);
      setNextPage(result.next ? nextPage + 1 : null);
    } catch {
      // non-fatal — the button stays so the customer can retry
    } finally {
      setIsLoadingMore(false);
    }
  }

  return (
    <PageShell size="xl">
      <div>
        <h1 className="text-2xl font-semibold text-text-primary">Our merchants</h1>
        <p className="text-sm text-text-muted">
          {isLoading
            ? "Meet the shops selling on MangiMall."
            : `${count} shops selling on MangiMall.`}
        </p>
      </div>

      {isLoading ? (
        <LoadingText />
      ) : error ? (
        <ErrorText>{error}</ErrorText>
      ) : shops.length === 0 ? (
        <EmptyText>No shops are open yet.</EmptyText>
      ) : (
        <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {shops.map((shop) => (
            <li key={shop.id} style={shopThemeStyle(shop)}>
              <Link href={`/shops/${shop.id}`} className="block h-full">
                <Card className="flex h-full flex-col gap-3 transition-shadow hover:shadow-md">
                  <div className="flex items-center gap-3">
                    <ShopLogo url={shop.logo_url} name={shop.name} size="md" />
                    <div className="min-w-0">
                      <h2 className="truncate font-semibold text-text-primary">{shop.name}</h2>
                      <p className="text-xs text-text-muted">
                        {shop.product_count} {shop.product_count === 1 ? "product" : "products"}
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
  );
}
