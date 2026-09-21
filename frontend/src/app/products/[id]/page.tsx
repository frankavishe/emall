"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { apiFetch, ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

type CatalogProductDetail = {
  id: number;
  name: string;
  description: string;
  price: string;
  category: { name: string; slug: string } | null;
  stock_status: "in_stock" | "out_of_stock";
  shop: { id: number; name: string };
  images: { id: number; url: string; position: number }[];
};

export default function ProductDetailPage() {
  const params = useParams<{ id: string }>();
  const { user } = useAuth();
  const [product, setProduct] = useState<CatalogProductDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [quantity, setQuantity] = useState(1);
  const [isAddingToCart, setIsAddingToCart] = useState(false);
  const [addToCartMessage, setAddToCartMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadProduct() {
      setIsLoading(true);
      setError(null);
      try {
        const result = await apiFetch<CatalogProductDetail>(`/api/catalog/products/${params.id}`);
        if (!cancelled) setProduct(result);
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof ApiError && err.status === 404
              ? "This product doesn't exist or is no longer available."
              : "Something went wrong. Please try again.",
          );
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    void loadProduct();
    return () => {
      cancelled = true;
    };
  }, [params.id]);

  async function handleAddToCart() {
    if (!product) return;
    setIsAddingToCart(true);
    setAddToCartMessage(null);
    try {
      await apiFetch("/api/cart/items", {
        method: "POST",
        body: JSON.stringify({ product_id: product.id, quantity }),
      });
      setAddToCartMessage("Added to cart.");
    } catch (err) {
      setAddToCartMessage(
        err instanceof ApiError ? err.message : "Something went wrong. Please try again.",
      );
    } finally {
      setIsAddingToCart(false);
    }
  }

  if (isLoading) {
    return (
      <main className="mx-auto flex min-h-screen max-w-3xl items-center justify-center px-6">
        <p className="text-sm text-black/60">Loading…</p>
      </main>
    );
  }

  if (error || !product) {
    return (
      <main className="mx-auto flex min-h-screen max-w-3xl flex-col items-center justify-center px-6 py-12">
        <p className="mb-4 text-sm text-red-600">{error ?? "Product not found."}</p>
        <Link href="/products" className="text-sm font-medium underline">
          Back to products
        </Link>
      </main>
    );
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col px-6 py-12">
      <Link href="/products" className="mb-6 text-sm font-medium underline">
        Back to products
      </Link>

      <div className="grid grid-cols-1 gap-8 md:grid-cols-2">
        <div className="flex flex-col gap-3">
          {product.images.length > 0 ? (
            product.images.map((image) => (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                key={image.id}
                src={image.url}
                alt={product.name}
                className="w-full rounded-md object-cover"
              />
            ))
          ) : (
            <div className="flex aspect-square w-full items-center justify-center rounded-md bg-black/5 text-sm text-black/40">
              No image
            </div>
          )}
        </div>

        <div>
          <h1 className="text-2xl font-semibold">{product.name}</h1>
          <p className="mt-1 text-sm text-black/60">Sold by {product.shop.name}</p>
          {product.category && (
            <p className="mt-1 text-sm text-black/60">Category: {product.category.name}</p>
          )}
          <p className="mt-4 text-xl font-medium">${product.price}</p>
          <p className="mt-1 text-sm text-black/60">
            {product.stock_status === "in_stock" ? "In stock" : "Out of stock"}
          </p>
          <p className="mt-6 whitespace-pre-line text-sm text-black/80">{product.description}</p>

          {product.stock_status === "in_stock" &&
            (!user ? (
              <p className="mt-6 text-sm text-black/60">
                <Link href="/login" className="font-medium underline">
                  Log in
                </Link>{" "}
                as a Customer to add this to your cart.
              </p>
            ) : user.role !== "CUSTOMER" ? (
              <p className="mt-6 text-sm text-black/60">
                Only Customer accounts can add items to a cart.
              </p>
            ) : (
              <div className="mt-6 flex items-center gap-3">
                <input
                  type="number"
                  min={1}
                  value={quantity}
                  onChange={(event) => setQuantity(Math.max(1, Number(event.target.value)))}
                  className="w-20 rounded-md border border-black/15 px-2 py-1 text-sm"
                />
                <button
                  type="button"
                  disabled={isAddingToCart}
                  onClick={() => void handleAddToCart()}
                  className="rounded-md bg-black px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
                >
                  Add to cart
                </button>
              </div>
            ))}
          {addToCartMessage && <p className="mt-2 text-sm text-black/60">{addToCartMessage}</p>}
        </div>
      </div>
    </main>
  );
}
