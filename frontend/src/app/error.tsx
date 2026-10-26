"use client"; // Error boundaries must be Client Components

import { useEffect } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";

export default function Error({
  error,
  retry,
}: {
  error: Error & { digest?: string };
  retry: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <ErrorState
      code="500"
      title="Something went wrong"
      description="An unexpected error occurred on our side. Please try again in a moment."
      actions={
        <>
          <Button onClick={() => retry()}>Try again</Button>
          <Button asChild variant="secondary">
            <Link href="/">Go home</Link>
          </Button>
        </>
      }
    >
      {error.digest && (
        <p className="font-mono text-xs text-text-muted">Reference: {error.digest}</p>
      )}
    </ErrorState>
  );
}
