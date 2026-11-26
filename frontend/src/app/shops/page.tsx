"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { listPublicShops, type CatalogShopListItem } from "@/lib/api-client";
import { ShopCard } from "@/components/shop-card";
import { PageShell } from "@/components/ui/page-shell";
import { Button } from "@/components/ui/button";
import { EmptyText, ErrorText, LoadingText } from "@/components/ui/status-text";

/** Public merchants directory: every approved shop, each card in the shop's own colors. */
export default function ShopsPage({
  searchParams,
}: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const { q } = use(searchParams);
  const query = typeof q === "string" ? q.trim() : "";
  // Keyed so a new ?q= starts the list over.
  return <ShopDirectory key={query} query={query} />;
}

function ShopDirectory({ query }: { query: string }) {
  const [shops, setShops] = useState<CatalogShopListItem[]>([]);
  const [count, setCount] = useState(0);
  const [nextPage, setNextPage] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listPublicShops(1, query)
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
  }, [query]);

  async function loadMore() {
    if (!nextPage) return;
    setIsLoadingMore(true);
    try {
      const result = await listPublicShops(nextPage, query);
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
        <h1 className="text-2xl font-semibold text-text-primary">
          {query ? `Shops matching “${query}”` : "Our merchants"}
        </h1>
        <p className="text-sm text-text-muted">
          {query ? (
            <>
              {isLoading ? "Searching…" : `${count} ${count === 1 ? "shop" : "shops"} found. `}
              <Link href="/shops" className="font-medium text-text-primary underline">
                Show all shops
              </Link>
            </>
          ) : isLoading ? (
            "Meet the shops selling on MangiMall."
          ) : (
            `${count} shops selling on MangiMall.`
          )}
        </p>
      </div>

      {isLoading ? (
        <LoadingText />
      ) : error ? (
        <ErrorText>{error}</ErrorText>
      ) : shops.length === 0 ? (
        <EmptyText>{query ? "No shops match your search." : "No shops are open yet."}</EmptyText>
      ) : (
        <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {shops.map((shop) => (
            <ShopCard key={shop.id} shop={shop} />
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
