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
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ErrorText, LoadingText, EmptyText } from "@/components/ui/status-text";

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
      <PageShell size="md" className="min-h-screen items-center justify-center">
        <LoadingText />
      </PageShell>
    );
  }

  return (
    <PageShell size="md" title="Feedback on your products">
      {error && <ErrorText>{error}</ErrorText>}

      {isLoadingReviews ? (
        <LoadingText>Loading reviews…</LoadingText>
      ) : !reviews || reviews.results.length === 0 ? (
        <EmptyText>No reviews on your products yet.</EmptyText>
      ) : (
        <>
          <ul className="flex flex-col gap-4">
            {reviews.results.map((review) => (
              <Card as="li" key={review.id} padding="sm">
                <div className="flex items-start justify-between">
                  <p className="font-medium text-text-primary">{review.product.name}</p>
                  <span aria-hidden="true" className="text-yellow-500">
                    {stars(review.rating)}
                  </span>
                </div>
                <p className="mt-1 text-sm text-text-muted">
                  {review.customer_display_name} &middot;{" "}
                  {new Date(review.created_at).toLocaleDateString()}
                </p>
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
