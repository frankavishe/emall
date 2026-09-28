import { ProductCatalog } from "@/components/product-catalog";
import { PageShell } from "@/components/ui/page-shell";

export default async function ProductsPage({
  searchParams,
}: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const { category } = await searchParams;
  const initialCategory = typeof category === "string" ? category : "";

  return (
    <PageShell size="xl" title="Products">
      {/* Keyed so following a different ?category= link resets the filters. */}
      <ProductCatalog key={initialCategory} initialCategory={initialCategory} />
    </PageShell>
  );
}
