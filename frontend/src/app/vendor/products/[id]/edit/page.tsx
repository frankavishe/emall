"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { apiFetch, ApiError } from "@/lib/api-client";

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
      <main className="mx-auto flex min-h-screen max-w-sm items-center justify-center px-6">
        <p className="text-sm text-black/60">{error ?? "Loading…"}</p>
      </main>
    );
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-sm flex-col justify-center px-6 py-12">
      <h1 className="mb-2 text-2xl font-semibold">Edit product</h1>
      <p className="mb-6 text-sm text-black/60">
        Shop: {product.shop.name} &middot; Status:{" "}
        {product.is_published ? "Published" : "Draft"}
      </p>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <label className="flex flex-col gap-1 text-sm font-medium">
          Name
          <input
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="rounded-md border border-black/15 px-3 py-2 text-base outline-none focus:border-black/40"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium">
          Description
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="rounded-md border border-black/15 px-3 py-2 text-base outline-none focus:border-black/40"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium">
          Price
          <input
            type="number"
            step="0.01"
            min="0"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            className="rounded-md border border-black/15 px-3 py-2 text-base outline-none focus:border-black/40"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium">
          Stock quantity
          <input
            type="number"
            step="1"
            min="0"
            value={stockQuantity}
            onChange={(e) => setStockQuantity(e.target.value)}
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
            <option value="">—</option>
            {categories.map((cat) => (
              <option key={cat.slug} value={cat.slug}>
                {cat.name}
              </option>
            ))}
          </select>
        </label>
        {error && <p className="text-sm text-red-600">{error}</p>}
        {message && <p className="text-sm text-green-700">{message}</p>}
        <div className="mt-2 flex gap-2">
          <button
            type="submit"
            disabled={isSubmitting}
            className="rounded-md bg-black px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {isSubmitting ? "Saving…" : "Save"}
          </button>
          <button
            type="button"
            disabled={isTogglingPublish}
            onClick={handlePublishToggle}
            className="rounded-md border border-black/15 px-4 py-2 text-sm font-medium disabled:opacity-50"
          >
            {product.is_published ? "Unpublish" : "Publish"}
          </button>
        </div>
      </form>
    </main>
  );
}
