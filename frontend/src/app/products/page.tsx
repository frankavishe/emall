"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch, ApiError } from "@/lib/api-client";
import { StarRating } from "@/components/star-rating";

type Category = { name: string; slug: string };

type CatalogProduct = {
  id: number;
  name: string;
  price: string;
  category: string | null;
  in_stock: boolean;
  shop_name: string;
  thumbnail_url: string | null;
  average_rating: number | null;
  review_count: number;
};

export default function ProductsPage() {
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
        setCategories(await apiFetch<Category[]>("/api/catalog/categories"));
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
        const params = new URLSearchParams();
        if (appliedFilters.q.trim()) params.set("q", appliedFilters.q.trim());
        if (appliedFilters.category) params.set("category", appliedFilters.category);
        if (appliedFilters.minPrice.trim()) {
          params.set("min_price", appliedFilters.minPrice.trim());
        }
        if (appliedFilters.maxPrice.trim()) {
          params.set("max_price", appliedFilters.maxPrice.trim());
        }
        const query = params.toString();
        const response = await apiFetch<{ results: CatalogProduct[] }>(
          `/api/catalog/products${query ? `?${query}` : ""}`,
        );
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
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col px-6 py-12">
      <h1 className="mb-6 text-2xl font-semibold">Products</h1>

      <form
        onSubmit={handleFilterSubmit}
        className="mb-8 flex flex-wrap items-end gap-3 rounded-md border border-black/15 p-4"
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

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

      {isLoading ? (
        <p className="text-sm text-black/60">Loading products…</p>
      ) : products.length === 0 ? (
        <p className="text-sm text-black/60">No products match your search.</p>
      ) : (
        <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3">
          {products.map((product) => (
            <li key={product.id} className="rounded-md border border-black/15 p-4">
              <Link href={`/products/${product.id}`} className="flex flex-col gap-2">
                {product.thumbnail_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={product.thumbnail_url}
                    alt={product.name}
                    className="aspect-square w-full rounded-md object-cover"
                  />
                ) : (
                  <div className="flex aspect-square w-full items-center justify-center rounded-md bg-black/5 text-sm text-black/40">
                    No image
                  </div>
                )}
                <p className="font-medium">{product.name}</p>
                <p className="text-sm text-black/60">{product.shop_name}</p>
                <p className="text-sm font-medium">${product.price}</p>
                <p className="text-sm text-black/60">
                  {product.in_stock ? "In stock" : "Out of stock"}
                </p>
                <StarRating rating={product.average_rating} reviewCount={product.review_count} />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
