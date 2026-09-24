"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import {
  ApiError,
  listVendorReviews,
  type PaginatedResponse,
  type VendorReview,
} from "@/lib/api-client";

function stars(rating: number) {
  return [1, 2, 3, 4, 5].map((star) => (star <= rating ? "★" : "☆")).join("");
}

export default function VendorReviewsPage() {
  const router = useRouter();
  const { user, isLoading } = useAuth();
  const [reviews, setReviews] = useState<PaginatedResponse<VendorReview> | null>(null);
  const [isLoadingReviews, setIsLoadingReviews] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  useEffect(() => {
    if (!isLoading && (!user || user.role !== "VENDOR")) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  useEffect(() => {
    if (user?.role !== "VENDOR") return;
    let cancelled = false;

    async function run() {
      setIsLoadingReviews(true);
      setError(null);
      try {
        const result = await listVendorReviews(page);
        if (!cancelled) setReviews(result);
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof ApiError ? err.message : "Something went wrong. Please try again.",
          );
        }
      } finally {
        if (!cancelled) setIsLoadingReviews(false);
      }
    }

    void run();
    return () => {
      cancelled = true;
    };
  }, [user, page]);

  if (isLoading || !user || user.role !== "VENDOR") {
    return (
      <main className="mx-auto flex min-h-screen max-w-3xl items-center justify-center px-6">
        <p className="text-sm text-black/60">Loading…</p>
      </main>
    );
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col px-6 py-12">
      <h1 className="mb-6 text-2xl font-semibold">Feedback on your products</h1>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

      {isLoadingReviews ? (
        <p className="text-sm text-black/60">Loading reviews…</p>
      ) : !reviews || reviews.results.length === 0 ? (
        <p className="text-sm text-black/60">No reviews on your products yet.</p>
      ) : (
        <>
          <ul className="flex flex-col gap-4">
            {reviews.results.map((review) => (
              <li key={review.id} className="rounded-md border border-black/15 p-4">
                <div className="flex items-start justify-between">
                  <p className="font-medium">{review.product.name}</p>
                  <span aria-hidden="true" className="text-yellow-500">
                    {stars(review.rating)}
                  </span>
                </div>
                <p className="mt-1 text-sm text-black/60">
                  {review.customer_display_name} &middot;{" "}
                  {new Date(review.created_at).toLocaleDateString()}
                </p>
                {review.comment && <p className="mt-2 text-sm">{review.comment}</p>}
              </li>
            ))}
          </ul>

          {(reviews.previous || reviews.next) && (
            <div className="mt-6 flex items-center justify-between">
              <button
                type="button"
                disabled={!reviews.previous}
                onClick={() => setPage((prev) => prev - 1)}
                className="rounded-md border border-black/15 px-3 py-1.5 text-sm font-medium disabled:opacity-50"
              >
                Previous
              </button>
              <button
                type="button"
                disabled={!reviews.next}
                onClick={() => setPage((prev) => prev + 1)}
                className="rounded-md border border-black/15 px-3 py-1.5 text-sm font-medium disabled:opacity-50"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </main>
  );
}
