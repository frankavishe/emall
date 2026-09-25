import { Suspense } from "react";
import ResetPasswordForm from "./reset-password-form";
import { PageShell } from "@/components/ui/page-shell";
import { LoadingText } from "@/components/ui/status-text";

export default function ResetPasswordPage() {
  return (
    <Suspense
      fallback={
        <PageShell size="sm" className="min-h-screen items-center justify-center">
          <LoadingText />
        </PageShell>
      }
    >
      <ResetPasswordForm />
    </Suspense>
  );
}
