import type { Metadata } from "next";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";

export const metadata: Metadata = {
  title: "Access denied · E-Mall",
};

export default function ForbiddenPage() {
  return (
    <ErrorState
      code="403"
      title="Access denied"
      description="Your account doesn't have permission to view this page."
      actions={
        <>
          <Button asChild>
            <Link href="/">Go home</Link>
          </Button>
          <Button asChild variant="secondary">
            <Link href="/login">Sign in with another account</Link>
          </Button>
        </>
      }
    />
  );
}
