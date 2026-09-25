import { ProductCatalog } from "@/components/product-catalog";
import { PageShell } from "@/components/ui/page-shell";

export default function ProductsPage() {
  return (
    <PageShell size="xl" title="Products">
      <ProductCatalog />
    </PageShell>
  );
}
