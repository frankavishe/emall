"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { listProducts, listPublicShops, listServices } from "@/lib/api-client";
import { useApi } from "@/lib/use-api";
import { ProductCard } from "@/components/product-card";
import { ServiceCard } from "@/components/booking/service-card";
import { ShopCard } from "@/components/shop-card";
import { MIN_QUERY_LENGTH, SiteSearch } from "@/components/site-search";
import { EmptyText, ErrorText, LoadingText } from "@/components/ui/status-text";

const PRODUCT_LIMIT = 8;
const SERVICE_LIMIT = 6;
const SHOP_LIMIT = 6;

/** The full results page: products, services and shops matching `query`, a section each. */
export function SearchResults({ query }: { query: string }) {
  const enabled = query.length >= MIN_QUERY_LENGTH;
  const products = useApi(
    () => listProducts({ q: query, limit: PRODUCT_LIMIT }),
    `products|${query}`,
    enabled,
  );
  const services = useApi(() => listServices({ search: query }), `services|${query}`, enabled);
  const shops = useApi(() => listPublicShops(1, query), `shops|${query}`, enabled);

  const encoded = encodeURIComponent(query);
  const sections = [products, services, shops];
  const settled = sections.every((section) => !section.isLoading);
  const total = sections.reduce((sum, section) => sum + (section.data?.count ?? 0), 0);
  const anyError = sections.some((section) => section.error);

  return (
    <div className="flex flex-col gap-8">
      <SiteSearch initialQuery={query} autoFocus={!query} className="max-w-2xl" />

      {!enabled ? (
        <EmptyText>
          {query
            ? `Type at least ${MIN_QUERY_LENGTH} characters to search.`
            : "Search for a product, a service like “haircut”, or a shop by name."}
        </EmptyText>
      ) : settled && total === 0 && !anyError ? (
        <EmptyText>
          Nothing matches &ldquo;{query}&rdquo;. Check the spelling, try a shorter word, or{" "}
          <Link href="/products" className="font-medium text-text-primary underline">
            browse all products
          </Link>
          .
        </EmptyText>
      ) : (
        <>
          <ResultSection
            title="Products"
            count={products.data?.count}
            viewAllHref={`/products?q=${encoded}`}
            isLoading={products.isLoading}
            error={products.error}
          >
            <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
              {products.data?.results.slice(0, PRODUCT_LIMIT).map((product) => (
                <ProductCard key={product.id} product={product} />
              ))}
            </ul>
          </ResultSection>

          <ResultSection
            title="Services"
            count={services.data?.count}
            viewAllHref={`/services?q=${encoded}`}
            isLoading={services.isLoading}
            error={services.error}
          >
            <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3">
              {services.data?.results.slice(0, SERVICE_LIMIT).map((service) => (
                <ServiceCard key={service.id} service={service} />
              ))}
            </ul>
          </ResultSection>

          <ResultSection
            title="Shops"
            count={shops.data?.count}
            viewAllHref={`/shops?q=${encoded}`}
            isLoading={shops.isLoading}
            error={shops.error}
          >
            <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {shops.data?.results.slice(0, SHOP_LIMIT).map((shop) => (
                <ShopCard key={shop.id} shop={shop} />
              ))}
            </ul>
          </ResultSection>
        </>
      )}
    </div>
  );
}

/** One result group. Hidden once loaded with no matches, so empty groups don't clutter. */
function ResultSection({
  title,
  count,
  viewAllHref,
  isLoading,
  error,
  children,
}: {
  title: string;
  count: number | undefined;
  viewAllHref: string;
  isLoading: boolean;
  error: string | null;
  children: ReactNode;
}) {
  if (!isLoading && !error && !count) return null;
  return (
    <section className="flex flex-col gap-3" aria-label={title}>
      <div className="flex items-baseline justify-between gap-4">
        <h2 className="text-lg font-semibold text-text-primary">
          {title}
          {count ? <span className="ml-2 text-sm font-normal text-text-muted">{count}</span> : null}
        </h2>
        {!!count && (
          <Link
            href={viewAllHref}
            className="text-sm font-medium text-text-primary hover:underline"
          >
            View all →
          </Link>
        )}
      </div>
      {isLoading ? (
        <LoadingText>Searching {title.toLowerCase()}…</LoadingText>
      ) : error ? (
        <ErrorText>{error}</ErrorText>
      ) : (
        children
      )}
    </section>
  );
}
