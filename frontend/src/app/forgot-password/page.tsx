"use client";

import { useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api-client";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FormField, inputClassName } from "@/components/ui/form-field";

const CONFIRMATION_MESSAGE = "If that email is registered, a reset link has been sent.";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setIsSubmitting(true);
    try {
      await apiFetch("/api/auth/password-reset/request", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
    } catch {
      // Intentionally ignored: the confirmation message never reveals whether the
      // email is registered or whether the request succeeded (FR-028, SC-010).
    } finally {
      setIsSubmitting(false);
      setSubmitted(true);
    }
  }

  return (
    <PageShell size="sm" className="min-h-screen justify-center">
      <Card>
        <h1 className="mb-6 text-2xl font-semibold text-text-primary">Reset your password</h1>
        {submitted ? (
          <p className="text-sm text-text-primary/80">{CONFIRMATION_MESSAGE}</p>
        ) : (
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
              {isSubmitting ? "Sending…" : "Send reset link"}
            </Button>
          </form>
        )}
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
