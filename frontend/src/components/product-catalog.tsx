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
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FormField, inputClassName } from "@/components/ui/form-field";
import { LoadingText, EmptyText, ErrorText } from "@/components/ui/status-text";

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
      <Card as="form" onSubmit={handleFilterSubmit} className="flex flex-wrap items-end gap-3">
        <FormField label="Search">
          <input
            type="text"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Keyword…"
            className={inputClassName}
          />
        </FormField>
        <FormField label="Category">
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className={inputClassName}
          >
            <option value="">All categories</option>
            {categories.map((c) => (
              <option key={c.slug} value={c.slug}>
                {c.name}
              </option>
            ))}
          </select>
        </FormField>
        <FormField label="Min price">
          <input
            type="number"
            min="0"
            step="0.01"
            value={minPrice}
            onChange={(e) => setMinPrice(e.target.value)}
            className={`w-28 ${inputClassName}`}
          />
        </FormField>
        <FormField label="Max price">
          <input
            type="number"
            min="0"
            step="0.01"
            value={maxPrice}
            onChange={(e) => setMaxPrice(e.target.value)}
            className={`w-28 ${inputClassName}`}
          />
        </FormField>
        <Button type="submit">Apply filters</Button>
      </Card>

      {error && <ErrorText>{error}</ErrorText>}

      {isLoading ? (
        <LoadingText>Loading products…</LoadingText>
      ) : products.length === 0 ? (
        <EmptyText>No products match your search.</EmptyText>
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
