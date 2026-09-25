"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { apiFetch, ApiError } from "@/lib/api-client";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FormField, inputClassName } from "@/components/ui/form-field";
import { ErrorText, LoadingText } from "@/components/ui/status-text";

type Category = { name: string; slug: string };
type VendorShop = { id: number; name: string; status: string };

export default function NewVendorProductPage() {
  const router = useRouter();
  const { user, isLoading } = useAuth();
  const [categories, setCategories] = useState<Category[]>([]);
  const approvedShops: VendorShop[] = (user?.shops ?? [])
    .filter((shop) => shop.status === "APPROVED")
    .map((shop) => ({ id: Number(shop.id), name: shop.name, status: shop.status }));

  const [shopId, setShopId] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [price, setPrice] = useState("");
  const [stockQuantity, setStockQuantity] = useState("");
  const [category, setCategory] = useState("");
  const [images, setImages] = useState<FileList | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (!isLoading && (!user || user.role !== "VENDOR")) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  useEffect(() => {
    async function loadCategories() {
      try {
        const result = await apiFetch<Category[]>("/api/catalog/categories");
        setCategories(result);
        if (result.length > 0) setCategory((prev) => prev || result[0].slug);
      } catch {
        // non-fatal — the form still works without a preselected category
      }
    }
    void loadCategories();
  }, []);

  const effectiveShopId = shopId || (approvedShops[0] ? String(approvedShops[0].id) : "");

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const formData = new FormData();
      formData.set("shop_id", effectiveShopId);
      formData.set("name", name);
      formData.set("description", description);
      // Omit blank optional fields entirely rather than sending "" — DRF's numeric/slug
      // fields reject an empty string, whereas an omitted field just stays unset on a draft.
      if (price.trim()) formData.set("price", price);
      if (stockQuantity.trim()) formData.set("stock_quantity", stockQuantity);
      if (category.trim()) formData.set("category", category);
      if (images) {
        Array.from(images).forEach((file) => formData.append("images", file));
      }

      const product = await apiFetch<{ id: number }>("/api/vendor/products", {
        method: "POST",
        body: formData,
      });
      router.push(`/vendor/products/${product.id}/edit`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isLoading || !user || user.role !== "VENDOR") {
    return (
      <PageShell size="sm" className="min-h-screen items-center justify-center">
        <LoadingText />
      </PageShell>
    );
  }

  if (approvedShops.length === 0) {
    return (
      <PageShell size="sm" className="min-h-screen justify-center">
        <Card>
          <h1 className="mb-4 text-2xl font-semibold text-text-primary">New product</h1>
          <p className="text-sm text-text-muted">
            You need at least one APPROVED shop before you can create a product.
          </p>
        </Card>
      </PageShell>
    );
  }

  return (
    <PageShell size="md">
      <Card>
        <h1 className="mb-6 text-2xl font-semibold text-text-primary">New product</h1>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <FormField label="Shop">
            <select
              required
              value={effectiveShopId}
              onChange={(e) => setShopId(e.target.value)}
              className={inputClassName}
            >
              {approvedShops.map((shop) => (
                <option key={shop.id} value={shop.id}>
                  {shop.name}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="Name">
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className={inputClassName}
            />
          </FormField>
          <FormField label="Description">
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className={inputClassName}
            />
          </FormField>
          <FormField label="Price">
            <input
              type="number"
              step="0.01"
              min="0"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              className={inputClassName}
            />
          </FormField>
          <FormField label="Stock quantity">
            <input
              type="number"
              step="1"
              min="0"
              value={stockQuantity}
              onChange={(e) => setStockQuantity(e.target.value)}
              className={inputClassName}
            />
          </FormField>
          <FormField label="Category">
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className={inputClassName}
            >
              <option value="">—</option>
              {categories.map((cat) => (
                <option key={cat.slug} value={cat.slug}>
                  {cat.name}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="Images">
            <input
              type="file"
              accept="image/*"
              multiple
              onChange={(e) => setImages(e.target.files)}
              className="text-sm text-text-primary"
            />
          </FormField>
          {error && <ErrorText>{error}</ErrorText>}
          <Button type="submit" disabled={isSubmitting} fullWidth className="mt-2">
            {isSubmitting ? "Creating…" : "Create product"}
          </Button>
        </form>
      </Card>
    </PageShell>
  );
}
