import { ProductCatalog } from "@/components/product-catalog";
import { PageShell } from "@/components/ui/page-shell";

export default async function ProductsPage({
  searchParams,
}: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const { category, q } = await searchParams;
  const initialCategory = typeof category === "string" ? category : "";
  const initialQuery = typeof q === "string" ? q.trim() : "";

  return (
    <PageShell size="xl" title="Products">
      {/* Keyed so following a different ?category= or ?q= link resets the filters. */}
      <ProductCatalog
        key={`${initialCategory}|${initialQuery}`}
        initialCategory={initialCategory}
        initialQuery={initialQuery}
      />
    </PageShell>
  );
}
