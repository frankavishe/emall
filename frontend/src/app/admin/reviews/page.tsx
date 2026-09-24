"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import {
  ApiError,
  deleteReviewAsAdmin,
  listAdminReviews,
  type AdminReview,
  type PaginatedResponse,
} from "@/lib/api-client";

function stars(rating: number) {
  return [1, 2, 3, 4, 5].map((star) => (star <= rating ? "★" : "☆")).join("");
}

export default function AdminReviewsPage() {
  const router = useRouter();
  const { user, isLoading } = useAuth();
  const [reviews, setReviews] = useState<PaginatedResponse<AdminReview> | null>(null);
  const [isLoadingReviews, setIsLoadingReviews] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [pendingActionId, setPendingActionId] = useState<number | null>(null);

  useEffect(() => {
    if (!isLoading && (!user || user.role !== "ADMINISTRATOR")) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  useEffect(() => {
    if (user?.role !== "ADMINISTRATOR") return;
    let cancelled = false;

    async function run() {
      setIsLoadingReviews(true);
      setError(null);
      try {
        const result = await listAdminReviews(page);
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

  async function handleRemove(reviewId: number) {
    setPendingActionId(reviewId);
    setError(null);
    try {
      await deleteReviewAsAdmin(reviewId);
      const result = await listAdminReviews(page);
      setReviews(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setPendingActionId(null);
    }
  }

  if (isLoading || !user || user.role !== "ADMINISTRATOR") {
    return (
      <main className="mx-auto flex min-h-screen max-w-3xl items-center justify-center px-6">
        <p className="text-sm text-black/60">Loading…</p>
      </main>
    );
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col px-6 py-12">
      <h1 className="mb-6 text-2xl font-semibold">Review moderation</h1>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

      {isLoadingReviews ? (
        <p className="text-sm text-black/60">Loading reviews…</p>
      ) : !reviews || reviews.results.length === 0 ? (
        <p className="text-sm text-black/60">No reviews to moderate.</p>
      ) : (
        <>
          <ul className="flex flex-col gap-4">
            {reviews.results.map((review) => (
              <li key={review.id} className="rounded-md border border-black/15 p-4">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-medium">{review.product.name}</p>
                    <p className="text-sm text-black/60">{review.shop.name}</p>
                    <p className="mt-1 text-sm text-black/60">{review.customer.email}</p>
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    <span aria-hidden="true" className="text-yellow-500">
                      {stars(review.rating)}
                    </span>
                    <button
                      type="button"
                      disabled={pendingActionId === review.id}
                      onClick={() => handleRemove(review.id)}
                      className="rounded-md border border-black/15 px-3 py-1.5 text-sm font-medium text-red-600 disabled:opacity-50"
                    >
                      Remove
                    </button>
                  </div>
                </div>
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
