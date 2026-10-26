import type { Metadata } from "next";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";

export const metadata: Metadata = {
  title: "Page not found · E-Mall",
};

export default function NotFound() {
  return (
    <ErrorState
      code="404"
      title="Page not found"
      description="The page you're looking for doesn't exist or has been moved."
      actions={
        <>
          <Button asChild>
            <Link href="/">Go home</Link>
          </Button>
          <Button asChild variant="secondary">
            <Link href="/products">Browse products</Link>
          </Button>
        </>
      }
    />
  );
}
