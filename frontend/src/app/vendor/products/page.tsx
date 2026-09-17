"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { apiFetch, ApiError } from "@/lib/api-client";

type VendorProduct = {
  id: number;
  shop: { id: number; name: string; status: string };
  name: string;
  description: string;
  price: string | null;
  stock_quantity: number | null;
  category: string | null;
  is_published: boolean;
  images: { id: number; url: string; position: number }[];
};

function isMissingFieldsBody(body: unknown): body is { missing_fields: string[] } {
  return (
    typeof body === "object" &&
    body !== null &&
    "missing_fields" in body &&
    Array.isArray((body as { missing_fields: unknown }).missing_fields)
  );
}

export default function VendorProductsPage() {
  const router = useRouter();
  const { user, isLoading } = useAuth();
  const [products, setProducts] = useState<VendorProduct[]>([]);
  const [isLoadingProducts, setIsLoadingProducts] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pendingActionId, setPendingActionId] = useState<number | null>(null);

  useEffect(() => {
    if (!isLoading && (!user || user.role !== "VENDOR")) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  const loadProducts = useCallback(async () => {
    setIsLoadingProducts(true);
    setError(null);
    try {
      const response = await apiFetch<{ results: VendorProduct[] }>("/api/vendor/products");
      setProducts(response.results);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setIsLoadingProducts(false);
    }
  }, []);

  useEffect(() => {
    if (user?.role !== "VENDOR") return;
    let cancelled = false;

    async function run() {
      setIsLoadingProducts(true);
      setError(null);
      try {
        const response = await apiFetch<{ results: VendorProduct[] }>("/api/vendor/products");
        if (!cancelled) setProducts(response.results);
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof ApiError ? err.message : "Something went wrong. Please try again.",
          );
        }
      } finally {
        if (!cancelled) setIsLoadingProducts(false);
      }
    }

    void run();
    return () => {
      cancelled = true;
    };
  }, [user]);

  async function handlePublishToggle(product: VendorProduct) {
    setPendingActionId(product.id);
    setError(null);
    try {
      const action = product.is_published ? "unpublish" : "publish";
      await apiFetch(`/api/vendor/products/${product.id}/${action}`, { method: "POST" });
      await loadProducts();
    } catch (err) {
      if (err instanceof ApiError && isMissingFieldsBody(err.body)) {
        setError(`Cannot publish — missing: ${err.body.missing_fields.join(", ")}`);
      } else {
        setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
      }
    } finally {
      setPendingActionId(null);
    }
  }

  async function handleDelete(product: VendorProduct) {
    setPendingActionId(product.id);
    setError(null);
    try {
      await apiFetch(`/api/vendor/products/${product.id}`, { method: "DELETE" });
      await loadProducts();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setPendingActionId(null);
    }
  }

  if (isLoading || !user || user.role !== "VENDOR") {
    return (
      <main className="mx-auto flex min-h-screen max-w-3xl items-center justify-center px-6">
        <p className="text-sm text-black/60">Loading…</p>
      </main>
    );
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col px-6 py-12">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">My products</h1>
        <Link
          href="/vendor/products/new"
          className="rounded-md bg-black px-4 py-2 text-sm font-medium text-white"
        >
          New product
        </Link>
      </div>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

      {isLoadingProducts ? (
        <p className="text-sm text-black/60">Loading products…</p>
      ) : products.length === 0 ? (
        <p className="text-sm text-black/60">You haven&apos;t created any products yet.</p>
      ) : (
        <ul className="flex flex-col gap-4">
          {products.map((product) => (
            <li key={product.id} className="rounded-md border border-black/15 p-4">
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-medium">{product.name}</p>
                  <p className="text-sm text-black/60">
                    Shop: {product.shop.name} ({product.shop.status})
                  </p>
                  <p className="mt-1 text-sm text-black/60">
                    Price: {product.price ?? "—"} &middot; Stock: {product.stock_quantity ?? "—"}{" "}
                    &middot; Category: {product.category ?? "—"}
                  </p>
                  <p className="mt-1 text-sm text-black/60">
                    Status: {product.is_published ? "Published" : "Draft"}
                  </p>
                </div>

                <div className="flex flex-col items-end gap-2">
                  <Link
                    href={`/vendor/products/${product.id}/edit`}
                    className="rounded-md border border-black/15 px-3 py-1.5 text-sm font-medium"
                  >
                    Edit
                  </Link>
                  <button
                    type="button"
                    disabled={pendingActionId === product.id}
                    onClick={() => handlePublishToggle(product)}
                    className="rounded-md border border-black/15 px-3 py-1.5 text-sm font-medium disabled:opacity-50"
                  >
                    {product.is_published ? "Unpublish" : "Publish"}
                  </button>
                  <button
                    type="button"
                    disabled={pendingActionId === product.id}
                    onClick={() => handleDelete(product)}
                    className="rounded-md border border-black/15 px-3 py-1.5 text-sm font-medium text-red-600 disabled:opacity-50"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
