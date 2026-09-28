"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api-client";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FormField, inputClassName } from "@/components/ui/form-field";

export default function ForgotPasswordPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setIsSubmitting(true);
    try {
      await apiFetch("/api/auth/password-reset/request", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
    } catch {
      // Intentionally ignored: the next step never reveals whether the email is
      // registered or whether the request succeeded (FR-028, SC-010).
    } finally {
      setIsSubmitting(false);
    }
    router.push(`/reset-password?email=${encodeURIComponent(email)}`);
  }

  return (
    <PageShell size="sm" className="min-h-screen justify-center">
      <Card>
        <h1 className="mb-2 text-2xl font-semibold text-text-primary">Reset your password</h1>
        <p className="mb-6 text-sm text-text-muted">
          Enter your account email and we&rsquo;ll send you a 6-digit code.
        </p>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <FormField label="Email">
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={inputClassName}
            />
          </FormField>
          <Button type="submit" disabled={isSubmitting} fullWidth className="mt-2">
            {isSubmitting ? "Sending…" : "Send code"}
          </Button>
        </form>
        <p className="mt-6 text-sm text-text-muted">
          Remembered your password?{" "}
          <Link href="/login" className="font-medium text-navy-900 underline">
            Log in
          </Link>
        </p>
      </Card>
    </PageShell>
  );
}
