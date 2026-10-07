"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { apiFetch, ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FormField, inputClassName } from "@/components/ui/form-field";
import { ErrorText } from "@/components/ui/status-text";

export default function VerifyEmailForm() {
  const searchParams = useSearchParams();
  const { user, refreshUser, resendVerificationEmail } = useAuth();
  const [emailInput, setEmailInput] = useState(() => searchParams.get("email") ?? "");
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [verified, setVerified] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const [resendMessage, setResendMessage] = useState<string | null>(null);

  // A logged-in user can only verify their own address.
  const email = user?.email ?? emailInput;

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    if (!/^\d{6}$/.test(code)) {
      setError("Enter the 6-digit code from your email.");
      return;
    }

    setIsSubmitting(true);
    try {
      await apiFetch<{ detail: string }>("/api/auth/verify-email/confirm", {
        method: "POST",
        body: JSON.stringify({ email, code }),
      });
      setVerified(true);
      if (user) {
        await refreshUser();
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleResend() {
    setResendMessage(null);
    setIsResending(true);
    try {
      await resendVerificationEmail();
      setCode("");
      setResendMessage("A new code has been sent. Any earlier code no longer works.");
    } catch (err) {
      setResendMessage(
        err instanceof ApiError ? err.message : "Something went wrong. Please try again.",
      );
    } finally {
      setIsResending(false);
    }
  }

  if (verified || user?.is_email_verified) {
    return (
      <PageShell size="sm" className="min-h-screen justify-center">
        <Card>
          <h1 className="mb-6 text-2xl font-semibold text-text-primary">Email verified</h1>
          <p className="text-sm text-text-primary/80">Your email address has been confirmed.</p>
          <Link
            href={user ? "/account" : "/login"}
            className="mt-6 inline-block text-sm font-medium text-brand-text underline"
          >
            {user ? "Go to your account" : "Log in"}
          </Link>
        </Card>
      </PageShell>
    );
  }

  return (
    <PageShell size="sm" className="min-h-screen justify-center">
      <Card>
        <h1 className="mb-2 text-2xl font-semibold text-text-primary">Verify your email</h1>
        <p className="mb-6 text-sm text-text-muted">
          We sent a 6-digit code to {user ? <strong>{user.email}</strong> : "your email"}. It
          expires in 10 minutes.
        </p>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {!user && (
            <FormField label="Email">
              <input
                type="email"
                required
                value={emailInput}
                onChange={(e) => setEmailInput(e.target.value)}
                className={inputClassName}
              />
            </FormField>
          )}
          <FormField label="Verification code">
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
          {error && <ErrorText>{error}</ErrorText>}
          <Button type="submit" disabled={isSubmitting} fullWidth className="mt-2">
            {isSubmitting ? "Verifying…" : "Verify email"}
          </Button>
        </form>

        {user ? (
          <div className="mt-6">
            <Button variant="secondary" onClick={handleResend} disabled={isResending}>
              {isResending ? "Sending…" : "Resend code"}
            </Button>
            {resendMessage && <p className="mt-2 text-sm text-text-muted">{resendMessage}</p>}
          </div>
        ) : (
          <p className="mt-6 text-sm text-text-muted">
            Need a new code?{" "}
            <Link href="/login" className="font-medium text-brand-text underline">
              Log in
            </Link>
            , then choose &ldquo;Verify now&rdquo; on your account page.
          </p>
        )}
      </Card>
    </PageShell>
  );
}
