"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { apiFetch, ApiError, submitReview } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { StarRating } from "@/components/star-rating";

type ProductReview = {
  id: number;
  customer_display_name: string;
  rating: number;
  comment: string;
  created_at: string;
};

type CatalogProductDetail = {
  id: number;
  name: string;
  description: string;
  price: string;
  category: { name: string; slug: string } | null;
  stock_status: "in_stock" | "out_of_stock";
  shop: { id: number; name: string };
  images: { id: number; url: string; position: number }[];
  average_rating: number | null;
  review_count: number;
  reviews: ProductReview[];
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
  const [reviewRating, setReviewRating] = useState(5);
  const [reviewComment, setReviewComment] = useState("");
  const [isSubmittingReview, setIsSubmittingReview] = useState(false);
  const [reviewMessage, setReviewMessage] = useState<string | null>(null);

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

  async function refreshProduct() {
    try {
      const result = await apiFetch<CatalogProductDetail>(`/api/catalog/products/${params.id}`);
      setProduct(result);
    } catch {
      // non-fatal — the page keeps showing the previously loaded product
    }
  }

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

  async function handleSubmitReview() {
    if (!product) return;
    setIsSubmittingReview(true);
    setReviewMessage(null);
    try {
      await submitReview(product.id, { rating: reviewRating, comment: reviewComment });
      setReviewMessage("Thanks for your review!");
      await refreshProduct();
    } catch (err) {
      setReviewMessage(
        err instanceof ApiError && err.status === 403
          ? "You can only review products you have received."
          : err instanceof ApiError
            ? err.message
            : "Something went wrong. Please try again.",
      );
    } finally {
      setIsSubmittingReview(false);
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
          <div className="mt-1">
            <StarRating rating={product.average_rating} reviewCount={product.review_count} />
          </div>
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

          {user && user.role === "CUSTOMER" && (
            <div className="mt-8 border-t border-black/10 pt-6">
              <h2 className="text-sm font-semibold">Leave a review</h2>
              <div className="mt-2 flex items-center gap-1">
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    key={star}
                    type="button"
                    onClick={() => setReviewRating(star)}
                    aria-label={`${star} star${star === 1 ? "" : "s"}`}
                    className={`text-2xl leading-none ${
                      star <= reviewRating ? "text-yellow-500" : "text-black/20"
                    }`}
                  >
                    ★
                  </button>
                ))}
              </div>
              <textarea
                value={reviewComment}
                onChange={(event) => setReviewComment(event.target.value)}
                placeholder="Write a comment (optional)"
                rows={3}
                className="mt-3 w-full rounded-md border border-black/15 px-3 py-2 text-sm"
              />
              <button
                type="button"
                disabled={isSubmittingReview}
                onClick={() => void handleSubmitReview()}
                className="mt-3 rounded-md bg-black px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
              >
                Submit review
              </button>
              {reviewMessage && <p className="mt-2 text-sm text-black/60">{reviewMessage}</p>}
            </div>
          )}

          <div className="mt-8 border-t border-black/10 pt-6">
            <h2 className="text-sm font-semibold">
              Reviews {product.review_count > 0 && `(${product.review_count})`}
            </h2>
            {product.reviews.length === 0 ? (
              <p className="mt-2 text-sm text-black/60">No reviews yet.</p>
            ) : (
              <ul className="mt-3 flex flex-col gap-4">
                {product.reviews.map((review) => (
                  <li key={review.id} className="border-b border-black/10 pb-4 last:border-0">
                    <div className="flex items-center gap-2">
                      <span aria-hidden="true" className="text-yellow-500">
                        {[1, 2, 3, 4, 5].map((star) => (star <= review.rating ? "★" : "☆")).join("")}
                      </span>
                      <span className="text-sm font-medium">{review.customer_display_name}</span>
                    </div>
                    {review.comment && (
                      <p className="mt-1 text-sm text-black/80">{review.comment}</p>
                    )}
                    <p className="mt-1 text-xs text-black/40">
                      {new Date(review.created_at).toLocaleDateString()}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
