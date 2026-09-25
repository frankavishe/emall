import { Suspense } from "react";
import VerifyEmailForm from "./verify-email-form";
import { PageShell } from "@/components/ui/page-shell";
import { LoadingText } from "@/components/ui/status-text";

export default function VerifyEmailPage() {
  return (
    <Suspense
      fallback={
        <PageShell size="sm" className="min-h-screen items-center justify-center">
          <LoadingText />
        </PageShell>
      }
    >
      <VerifyEmailForm />
    </Suspense>
  );
}
