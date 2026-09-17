"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { apiFetch, ApiError } from "@/lib/api-client";

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
      <main className="mx-auto flex min-h-screen max-w-sm items-center justify-center px-6">
        <p className="text-sm text-black/60">Loading…</p>
      </main>
    );
  }

  if (approvedShops.length === 0) {
    return (
      <main className="mx-auto flex min-h-screen max-w-sm flex-col justify-center px-6 py-12">
        <h1 className="mb-4 text-2xl font-semibold">New product</h1>
        <p className="text-sm text-black/60">
          You need at least one APPROVED shop before you can create a product.
        </p>
      </main>
    );
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-sm flex-col justify-center px-6 py-12">
      <h1 className="mb-6 text-2xl font-semibold">New product</h1>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <label className="flex flex-col gap-1 text-sm font-medium">
          Shop
          <select
            required
            value={effectiveShopId}
            onChange={(e) => setShopId(e.target.value)}
            className="rounded-md border border-black/15 px-3 py-2 text-base outline-none focus:border-black/40"
          >
            {approvedShops.map((shop) => (
              <option key={shop.id} value={shop.id}>
                {shop.name}
              </option>
            ))}
          </select>
        </label>
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
        <label className="flex flex-col gap-1 text-sm font-medium">
          Images
          <input
            type="file"
            accept="image/*"
            multiple
            onChange={(e) => setImages(e.target.files)}
            className="text-sm"
          />
        </label>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={isSubmitting}
          className="mt-2 rounded-md bg-black px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {isSubmitting ? "Creating…" : "Create product"}
        </button>
      </form>
    </main>
  );
}
