"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { listAdminProducts } from "@/lib/api-client";
import { formatCurrency } from "@/lib/currency";
import { useApi, useRequireRole } from "@/lib/use-api";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Pill } from "@/components/ui/pill";
import { SegmentedToggle } from "@/components/ui/segmented-toggle";
import { FormField, inputClassName } from "@/components/ui/form-field";
import { EmptyText, ErrorText, LoadingText } from "@/components/ui/status-text";
import { Pager } from "@/components/pager";

type PublishedFilter = "" | "true" | "false";

export default function AdminProductsPage() {
  return (
    <Suspense fallback={<LoadingText />}>
      <AdminProducts />
    </Suspense>
  );
}

function AdminProducts() {
  const allowed = useRequireRole("ADMINISTRATOR");
  // `?shop=<id>` (linked from a shop's detail page) narrows to one shop.
  const shop = useSearchParams().get("shop") ?? "";
  const [published, setPublished] = useState<PublishedFilter>("");
  const [search, setSearch] = useState("");
  const [searchDraft, setSearchDraft] = useState("");
  const [page, setPage] = useState(1);
  const products = useApi(
    () =>
      listAdminProducts({
        page,
        shop,
        search,
        published: published === "" ? undefined : published === "true",
      }),
    `${page}|${shop}|${search}|${published}`,
    allowed,
  );

  if (!allowed) {
    return (
      <PageShell size="md" className="min-h-screen items-center justify-center">
        <LoadingText />
      </PageShell>
    );
  }

  return (
    <PageShell
      size="lg"
      title="All products"
      description={
        shop
          ? "Products of one shop."
          : "Every product in the mall, including drafts and deleted ones."
      }
      actions={
        shop ? (
          <Button asChild variant="ghost" size="sm">
            <Link href="/admin/products">Show all shops</Link>
          </Button>
        ) : undefined
      }
    >
      <div className="flex flex-wrap items-end gap-3">
        <form
          className="flex items-end gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            setSearch(searchDraft.trim());
            setPage(1);
          }}
        >
          <FormField label="Search">
            <input
              type="search"
              placeholder="Product name"
              value={searchDraft}
              onChange={(e) => setSearchDraft(e.target.value)}
              className={inputClassName}
            />
          </FormField>
          <Button type="submit" variant="secondary" size="sm">
            Search
          </Button>
        </form>
        <SegmentedToggle
          options={[
            { value: "", label: "ALL" },
            { value: "true", label: "PUBLISHED" },
            { value: "false", label: "DRAFT" },
          ]}
          value={published}
          onChange={(value) => {
            setPublished(value);
            setPage(1);
          }}
        />
      </div>

      {products.error && <ErrorText>{products.error}</ErrorText>}
      {products.isLoading && !products.data ? (
        <LoadingText>Loading products…</LoadingText>
      ) : !products.data || products.data.results.length === 0 ? (
        <EmptyText>No products match.</EmptyText>
      ) : (
        <>
          <p className="text-sm text-text-muted">{products.data.count} products</p>
          <ul className="flex flex-col gap-3">
            {products.data.results.map((product) => (
              <Card
                as="li"
                key={product.id}
                padding="sm"
                className="flex flex-wrap items-start justify-between gap-3"
              >
                <div>
                  <p className="font-medium text-text-primary">
                    {product.is_deleted ? (
                      product.name
                    ) : (
                      <Link href={`/products/${product.id}`} className="hover:underline">
                        {product.name}
                      </Link>
                    )}
                  </p>
                  <p className="text-sm text-text-muted">
                    <Link href={`/admin/shops/${product.shop.id}`} className="underline">
                      {product.shop.name}
                    </Link>
                    {product.category ? ` · ${product.category}` : ""} &middot;{" "}
                    {product.price ? formatCurrency(product.price) : "no price"} &middot; stock{" "}
                    {product.stock_quantity ?? "—"}
                  </p>
                  <div className="mt-1 flex flex-wrap gap-2">
                    {product.is_deleted ? (
                      <Pill tone="cancelled">DELETED</Pill>
                    ) : product.is_published ? (
                      <Pill tone="approved">PUBLISHED</Pill>
                    ) : (
                      <Pill tone="neutral">DRAFT</Pill>
                    )}
                  </div>
                </div>
                <div className="text-right text-sm">
                  <p className="font-medium text-text-primary">{formatCurrency(product.revenue)}</p>
                  <p className="text-text-muted">{product.units_sold} sold</p>
                </div>
              </Card>
            ))}
          </ul>
          <Pager
            previous={products.data.previous}
            next={products.data.next}
            onPrevious={() => setPage((p) => p - 1)}
            onNext={() => setPage((p) => p + 1)}
          />
        </>
      )}
    </PageShell>
  );
}
