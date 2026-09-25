"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { apiFetch, ApiError } from "@/lib/api-client";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FormField, inputClassName } from "@/components/ui/form-field";
import { Pill } from "@/components/ui/pill";
import { ErrorText, LoadingText } from "@/components/ui/status-text";

type Category = { name: string; slug: string };

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

export default function EditVendorProductPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const { user, isLoading } = useAuth();
  const [categories, setCategories] = useState<Category[]>([]);
  const [product, setProduct] = useState<VendorProduct | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [price, setPrice] = useState("");
  const [stockQuantity, setStockQuantity] = useState("");
  const [category, setCategory] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isTogglingPublish, setIsTogglingPublish] = useState(false);

  useEffect(() => {
    if (!isLoading && (!user || user.role !== "VENDOR")) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  useEffect(() => {
    async function loadCategories() {
      try {
        setCategories(await apiFetch<Category[]>("/api/catalog/categories"));
      } catch {
        // non-fatal
      }
    }
    void loadCategories();
  }, []);

  useEffect(() => {
    if (user?.role !== "VENDOR") return;
    async function loadProduct() {
      try {
        const results = await apiFetch<{ results: VendorProduct[] }>("/api/vendor/products");
        const found = results.results.find((p) => String(p.id) === params.id);
        if (!found) {
          setError("Product not found.");
          return;
        }
        setProduct(found);
        setName(found.name);
        setDescription(found.description);
        setPrice(found.price ?? "");
        setStockQuantity(found.stock_quantity !== null ? String(found.stock_quantity) : "");
        setCategory(found.category ?? "");
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Something went wrong.");
      }
    }
    void loadProduct();
  }, [user, params.id]);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    setIsSubmitting(true);
    try {
      const formData = new FormData();
      formData.set("name", name);
      formData.set("description", description);
      // Omit blank optional fields entirely rather than sending "" — DRF's numeric/slug
      // fields reject an empty string; an omitted field just leaves the existing value as-is.
      if (price.trim()) formData.set("price", price);
      if (stockQuantity.trim()) formData.set("stock_quantity", stockQuantity);
      if (category.trim()) formData.set("category", category);

      const updated = await apiFetch<VendorProduct>(`/api/vendor/products/${params.id}`, {
        method: "PATCH",
        body: formData,
      });
      setProduct(updated);
      setMessage("Saved.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handlePublishToggle() {
    if (!product) return;
    setIsTogglingPublish(true);
    setError(null);
    setMessage(null);
    try {
      const action = product.is_published ? "unpublish" : "publish";
      await apiFetch(`/api/vendor/products/${params.id}/${action}`, { method: "POST" });
      setProduct({ ...product, is_published: !product.is_published });
      setMessage(product.is_published ? "Unpublished." : "Published.");
    } catch (err) {
      if (err instanceof ApiError && isMissingFieldsBody(err.body)) {
        setError(`Cannot publish — missing: ${err.body.missing_fields.join(", ")}`);
      } else {
        setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
      }
    } finally {
      setIsTogglingPublish(false);
    }
  }

  if (isLoading || !user || user.role !== "VENDOR" || !product) {
    return (
      <PageShell size="sm" className="min-h-screen items-center justify-center">
        {error ? <ErrorText>{error}</ErrorText> : <LoadingText />}
      </PageShell>
    );
  }

  return (
    <PageShell size="md">
      <Card>
        <h1 className="mb-2 text-2xl font-semibold text-text-primary">Edit product</h1>
        <p className="mb-6 flex items-center gap-2 text-sm text-text-muted">
          Shop: {product.shop.name}
          <Pill tone={product.is_published ? "delivered" : "neutral"}>
            {product.is_published ? "Published" : "Draft"}
          </Pill>
        </p>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
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
          {error && <ErrorText>{error}</ErrorText>}
          {message && <p className="text-sm text-status-approved">{message}</p>}
          <div className="mt-2 flex gap-2">
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Saving…" : "Save"}
            </Button>
            <Button
              type="button"
              variant="secondary"
              disabled={isTogglingPublish}
              onClick={handlePublishToggle}
            >
              {product.is_published ? "Unpublish" : "Publish"}
            </Button>
          </div>
        </form>
      </Card>
    </PageShell>
  );
}
