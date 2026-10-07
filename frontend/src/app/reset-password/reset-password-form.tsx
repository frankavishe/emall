"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { apiFetch, ApiError } from "@/lib/api-client";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FormField, inputClassName } from "@/components/ui/form-field";
import { ErrorText } from "@/components/ui/status-text";

const SENT_MESSAGE = "If that email is registered, a reset code has been sent.";

export default function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState(() => searchParams.get("email") ?? "");
  const [code, setCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const [resendMessage, setResendMessage] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    if (!/^\d{6}$/.test(code)) {
      setError("Enter the 6-digit code from your email.");
      return;
    }

    setIsSubmitting(true);
    try {
      await apiFetch("/api/auth/password-reset/confirm", {
        method: "POST",
        body: JSON.stringify({ email, code, new_password: newPassword }),
      });
      router.push("/login");
    } catch (err) {
      if (err instanceof ApiError) {
        // Password-strength failures come back as field errors, not a `detail`.
        const body = err.body as { new_password?: string[] } | null;
        setError(body?.new_password?.join(" ") ?? err.message);
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleResend() {
    setResendMessage(null);
    setIsResending(true);
    try {
      await apiFetch("/api/auth/password-reset/request", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
    } catch {
      // Same non-disclosure as the forgot-password page.
    } finally {
      setIsResending(false);
      setCode("");
      setResendMessage(SENT_MESSAGE);
    }
  }

  return (
    <PageShell size="sm" className="min-h-screen justify-center">
      <Card>
        <h1 className="mb-2 text-2xl font-semibold text-text-primary">Set a new password</h1>
        <p className="mb-6 text-sm text-text-muted">
          {SENT_MESSAGE} Enter it below — it expires in 10 minutes.
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
          <FormField label="Reset code">
            <input
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              pattern="\d{6}"
              maxLength={6}
              required
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
              className={`${inputClassName} tracking-[0.5em]`}
            />
          </FormField>
          <FormField label="New password">
            <input
              type="password"
              autoComplete="new-password"
              required
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className={inputClassName}
            />
          </FormField>
          {error && <ErrorText>{error}</ErrorText>}
          <Button type="submit" disabled={isSubmitting} fullWidth className="mt-2">
            {isSubmitting ? "Updating…" : "Update password"}
          </Button>
        </form>

        <div className="mt-6">
          <Button variant="secondary" onClick={handleResend} disabled={isResending || !email}>
            {isResending ? "Sending…" : "Resend code"}
          </Button>
          {resendMessage && <p className="mt-2 text-sm text-text-muted">{resendMessage}</p>}
        </div>

        <p className="mt-6 text-sm text-text-muted">
          Remembered your password?{" "}
          <Link href="/login" className="font-medium text-brand-text underline">
            Log in
          </Link>
        </p>
      </Card>
    </PageShell>
  );
}
