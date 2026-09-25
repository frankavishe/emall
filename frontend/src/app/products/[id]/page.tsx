"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { apiFetch, ApiError, submitReview } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { StarRating } from "@/components/star-rating";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ErrorText, LoadingText, EmptyText } from "@/components/ui/status-text";
import { cn } from "@/lib/cn";

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
      <PageShell size="lg" className="min-h-screen items-center justify-center">
        <LoadingText />
      </PageShell>
    );
  }

  if (error || !product) {
    return (
      <PageShell size="lg" className="min-h-screen items-center justify-center">
        <ErrorText>{error ?? "Product not found."}</ErrorText>
        <Link href="/products" className="text-sm font-medium text-navy-900 underline">
          Back to products
        </Link>
      </PageShell>
    );
  }

  return (
    <PageShell size="lg">
      <Link href="/products" className="text-sm font-medium text-navy-900 underline">
        Back to products
      </Link>

      <Card className="grid grid-cols-1 gap-8 md:grid-cols-2">
        <div className="flex flex-col gap-3">
          {product.images.length > 0 ? (
            product.images.map((image) => (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                key={image.id}
                src={image.url}
                alt={product.name}
                className="w-full rounded-control object-cover"
              />
            ))
          ) : (
            <div className="flex aspect-square w-full items-center justify-center rounded-control bg-card-muted text-sm text-text-muted">
              No image
            </div>
          )}
        </div>

        <div>
          <h1 className="text-2xl font-semibold text-text-primary">{product.name}</h1>
          <p className="mt-1 text-sm text-text-muted">Sold by {product.shop.name}</p>
          {product.category && (
            <p className="mt-1 text-sm text-text-muted">Category: {product.category.name}</p>
          )}
          <p className="mt-4 text-xl font-medium text-text-primary">${product.price}</p>
          <p className="mt-1 text-sm text-text-muted">
            {product.stock_status === "in_stock" ? "In stock" : "Out of stock"}
          </p>
          <div className="mt-1">
            <StarRating rating={product.average_rating} reviewCount={product.review_count} />
          </div>
          <p className="mt-6 whitespace-pre-line text-sm text-text-primary/80">
            {product.description}
          </p>

          {product.stock_status === "in_stock" &&
            (!user ? (
              <p className="mt-6 text-sm text-text-muted">
                <Link href="/login" className="font-medium text-navy-900 underline">
                  Log in
                </Link>{" "}
                as a Customer to add this to your cart.
              </p>
            ) : user.role !== "CUSTOMER" ? (
              <p className="mt-6 text-sm text-text-muted">
                Only Customer accounts can add items to a cart.
              </p>
            ) : (
              <div className="mt-6 flex items-center gap-3">
                <input
                  type="number"
                  min={1}
                  value={quantity}
                  onChange={(event) => setQuantity(Math.max(1, Number(event.target.value)))}
                  className="w-20 rounded-control border border-border px-2 py-1 text-sm"
                />
                <Button disabled={isAddingToCart} onClick={() => void handleAddToCart()}>
                  Add to cart
                </Button>
              </div>
            ))}
          {addToCartMessage && <p className="mt-2 text-sm text-text-muted">{addToCartMessage}</p>}

          {user && user.role === "CUSTOMER" && (
            <div className="mt-8 border-t border-border pt-6">
              <h2 className="text-sm font-semibold text-text-primary">Leave a review</h2>
              <div className="mt-2 flex items-center gap-1">
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    key={star}
                    type="button"
                    onClick={() => setReviewRating(star)}
                    aria-label={`${star} star${star === 1 ? "" : "s"}`}
                    className={cn(
                      "text-2xl leading-none",
                      star <= reviewRating ? "text-yellow-500" : "text-text-muted/40",
                    )}
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
                className="mt-3 w-full rounded-control border border-border px-3 py-2 text-sm"
              />
              <Button
                disabled={isSubmittingReview}
                onClick={() => void handleSubmitReview()}
                className="mt-3"
              >
                Submit review
              </Button>
              {reviewMessage && <p className="mt-2 text-sm text-text-muted">{reviewMessage}</p>}
            </div>
          )}

          <div className="mt-8 border-t border-border pt-6">
            <h2 className="text-sm font-semibold text-text-primary">
              Reviews {product.review_count > 0 && `(${product.review_count})`}
            </h2>
            {product.reviews.length === 0 ? (
              <EmptyText>No reviews yet.</EmptyText>
            ) : (
              <ul className="mt-3 flex flex-col gap-4">
                {product.reviews.map((review) => (
                  <li key={review.id} className="border-b border-border pb-4 last:border-0">
                    <div className="flex items-center gap-2">
                      <span aria-hidden="true" className="text-yellow-500">
                        {[1, 2, 3, 4, 5]
                          .map((star) => (star <= review.rating ? "★" : "☆"))
                          .join("")}
                      </span>
                      <span className="text-sm font-medium text-text-primary">
                        {review.customer_display_name}
                      </span>
                    </div>
                    {review.comment && (
                      <p className="mt-1 text-sm text-text-primary/80">{review.comment}</p>
                    )}
                    <p className="mt-1 text-xs text-text-muted">
                      {new Date(review.created_at).toLocaleDateString()}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </Card>
    </PageShell>
  );
}
