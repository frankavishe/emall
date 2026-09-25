"use client";

import { useEffect, useState } from "react";
import {
  listProducts,
  listCategories,
  ApiError,
  type CatalogProduct,
  type Category,
} from "@/lib/api-client";
import { ProductCard } from "@/components/product-card";

export function ProductCatalog() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [products, setProducts] = useState<CatalogProduct[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [appliedFilters, setAppliedFilters] = useState({
    q: "",
    category: "",
    minPrice: "",
    maxPrice: "",
  });

  useEffect(() => {
    async function loadCategories() {
      try {
        setCategories(await listCategories());
      } catch {
        // non-fatal — the page still works without a category dropdown
      }
    }
    void loadCategories();
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadProducts() {
      setIsLoading(true);
      setError(null);
      try {
        const response = await listProducts({
          q: appliedFilters.q,
          category: appliedFilters.category,
          minPrice: appliedFilters.minPrice,
          maxPrice: appliedFilters.maxPrice,
        });
        if (!cancelled) setProducts(response.results);
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof ApiError ? err.message : "Something went wrong. Please try again.",
          );
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    void loadProducts();
    return () => {
      cancelled = true;
    };
  }, [appliedFilters]);

  function handleFilterSubmit(event: React.FormEvent) {
    event.preventDefault();
    setAppliedFilters({ q, category, minPrice, maxPrice });
  }

  return (
    <div className="flex flex-col gap-6">
      <form
        onSubmit={handleFilterSubmit}
        className="flex flex-wrap items-end gap-3 rounded-md border border-black/15 p-4"
      >
        <label className="flex flex-col gap-1 text-sm font-medium">
          Search
          <input
            type="text"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Keyword…"
            className="rounded-md border border-black/15 px-3 py-2 text-base outline-none focus:border-black/40"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium">
          Category
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="rounded-md border border-black/15 px-3 py-2 text-base outline-none focus:border-black/40"
          >
            <option value="">All categories</option>
            {categories.map((c) => (
              <option key={c.slug} value={c.slug}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium">
          Min price
          <input
            type="number"
            min="0"
            step="0.01"
            value={minPrice}
            onChange={(e) => setMinPrice(e.target.value)}
            className="w-28 rounded-md border border-black/15 px-3 py-2 text-base outline-none focus:border-black/40"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium">
          Max price
          <input
            type="number"
            min="0"
            step="0.01"
            value={maxPrice}
            onChange={(e) => setMaxPrice(e.target.value)}
            className="w-28 rounded-md border border-black/15 px-3 py-2 text-base outline-none focus:border-black/40"
          />
        </label>
        <button
          type="submit"
          className="rounded-md bg-black px-4 py-2 text-sm font-medium text-white"
        >
          Apply filters
        </button>
      </form>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {isLoading ? (
        <p className="text-sm text-black/60">Loading products…</p>
      ) : products.length === 0 ? (
        <p className="text-sm text-black/60">No products match your search.</p>
      ) : (
        <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
          {products.map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </ul>
      )}
    </div>
  );
}
