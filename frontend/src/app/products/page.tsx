import { ProductCatalog } from "@/components/product-catalog";

export default function ProductsPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-6xl flex-col px-6 py-12">
      <h1 className="mb-6 text-2xl font-semibold">Products</h1>
      <ProductCatalog />
    </main>
  );
}
