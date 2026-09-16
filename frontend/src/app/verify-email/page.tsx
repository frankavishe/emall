import { Suspense } from "react";
import VerifyEmailForm from "./verify-email-form";

export default function VerifyEmailPage() {
  return (
    <Suspense
      fallback={
        <main className="mx-auto flex min-h-screen max-w-sm items-center justify-center px-6">
          <p className="text-sm text-black/60">Loading…</p>
        </main>
      }
    >
      <VerifyEmailForm />
    </Suspense>
  );
}
