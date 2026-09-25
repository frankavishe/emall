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
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ErrorText, LoadingText, EmptyText } from "@/components/ui/status-text";

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
      <PageShell size="md" className="min-h-screen items-center justify-center">
        <LoadingText />
      </PageShell>
    );
  }

  return (
    <PageShell size="md" title="Review moderation">
      {error && <ErrorText>{error}</ErrorText>}

      {isLoadingReviews ? (
        <LoadingText>Loading reviews…</LoadingText>
      ) : !reviews || reviews.results.length === 0 ? (
        <EmptyText>No reviews to moderate.</EmptyText>
      ) : (
        <>
          <ul className="flex flex-col gap-4">
            {reviews.results.map((review) => (
              <Card as="li" key={review.id} padding="sm">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-text-primary">{review.product.name}</p>
                    <p className="text-sm text-text-muted">{review.shop.name}</p>
                    <p className="mt-1 truncate text-sm text-text-muted">{review.customer.email}</p>
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-2">
                    <span aria-hidden="true" className="text-yellow-500">
                      {stars(review.rating)}
                    </span>
                    <Button
                      variant="danger"
                      size="sm"
                      disabled={pendingActionId === review.id}
                      onClick={() => handleRemove(review.id)}
                    >
                      Remove
                    </Button>
                  </div>
                </div>
                {review.comment && (
                  <p className="mt-2 text-sm text-text-primary">{review.comment}</p>
                )}
              </Card>
            ))}
          </ul>

          {(reviews.previous || reviews.next) && (
            <div className="flex items-center justify-between">
              <Button
                variant="secondary"
                disabled={!reviews.previous}
                onClick={() => setPage((prev) => prev - 1)}
              >
                Previous
              </Button>
              <Button
                variant="secondary"
                disabled={!reviews.next}
                onClick={() => setPage((prev) => prev + 1)}
              >
                Next
              </Button>
            </div>
          )}
        </>
      )}
    </PageShell>
  );
}
