"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { apiFetch, ApiError } from "@/lib/api-client";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Pill } from "@/components/ui/pill";
import { ErrorText, LoadingText, EmptyText } from "@/components/ui/status-text";

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
      <PageShell size="md" className="min-h-screen items-center justify-center">
        <LoadingText />
      </PageShell>
    );
  }

  return (
    <PageShell
      size="md"
      title="My products"
      actions={
        <Button asChild>
          <Link href="/vendor/products/new">New product</Link>
        </Button>
      }
    >
      {error && <ErrorText>{error}</ErrorText>}

      {isLoadingProducts ? (
        <LoadingText>Loading products…</LoadingText>
      ) : products.length === 0 ? (
        <EmptyText>You haven&apos;t created any products yet.</EmptyText>
      ) : (
        <ul className="flex flex-col gap-4">
          {products.map((product) => (
            <Card as="li" key={product.id} padding="sm">
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-medium text-text-primary">{product.name}</p>
                  <p className="text-sm text-text-muted">
                    Shop: {product.shop.name} ({product.shop.status})
                  </p>
                  <p className="mt-1 text-sm text-text-muted">
                    Price: {product.price ?? "—"} &middot; Stock: {product.stock_quantity ?? "—"}{" "}
                    &middot; Category: {product.category ?? "—"}
                  </p>
                  <div className="mt-2">
                    <Pill tone={product.is_published ? "delivered" : "neutral"}>
                      {product.is_published ? "Published" : "Draft"}
                    </Pill>
                  </div>
                </div>

                <div className="flex flex-col items-end gap-2">
                  <Button variant="secondary" size="sm" asChild>
                    <Link href={`/vendor/products/${product.id}/edit`}>Edit</Link>
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={pendingActionId === product.id}
                    onClick={() => handlePublishToggle(product)}
                  >
                    {product.is_published ? "Unpublish" : "Publish"}
                  </Button>
                  <Button
                    variant="danger"
                    size="sm"
                    disabled={pendingActionId === product.id}
                    onClick={() => handleDelete(product)}
                  >
                    Delete
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </ul>
      )}
    </PageShell>
  );
}
