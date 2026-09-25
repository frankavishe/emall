"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { apiFetch, ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";

type Status = "verifying" | "success" | "error";

export default function VerifyEmailForm() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const { user, resendVerificationEmail } = useAuth();
  const [status, setStatus] = useState<Status>(() => (token ? "verifying" : "error"));
  const [message, setMessage] = useState(() =>
    token ? "Verifying your email…" : "This verification link is missing a token.",
  );
  const [isResending, setIsResending] = useState(false);
  const [resendMessage, setResendMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      return;
    }

    let cancelled = false;
    (async () => {
      try {
        const result = await apiFetch<{ detail: string }>("/api/auth/verify-email/confirm", {
          method: "POST",
          body: JSON.stringify({ token }),
        });
        if (cancelled) return;
        setStatus("success");
        setMessage(result.detail);
      } catch (err) {
        if (cancelled) return;
        setStatus("error");
        setMessage(
          err instanceof ApiError
            ? err.message
            : "This verification link is invalid or has expired.",
        );
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [token]);

  async function handleResend() {
    setResendMessage(null);
    setIsResending(true);
    try {
      await resendVerificationEmail();
      setResendMessage("A new verification link has been sent.");
    } catch (err) {
      setResendMessage(
        err instanceof ApiError ? err.message : "Something went wrong. Please try again.",
      );
    } finally {
      setIsResending(false);
    }
  }

  return (
    <PageShell size="sm" className="min-h-screen justify-center">
      <Card>
        <h1 className="mb-6 text-2xl font-semibold text-text-primary">Email verification</h1>
        <p
          className={cn(
            "text-sm",
            status === "error" ? "text-status-cancelled" : "text-text-primary/80",
          )}
        >
          {message}
        </p>

        {status === "error" && user && (
          <div className="mt-6">
            <Button variant="secondary" onClick={handleResend} disabled={isResending}>
              {isResending ? "Sending…" : "Resend verification email"}
            </Button>
            {resendMessage && <p className="mt-2 text-sm text-text-muted">{resendMessage}</p>}
          </div>
        )}

        {status === "success" && (
          <Link
            href="/account"
            className="mt-6 inline-block text-sm font-medium text-navy-900 underline"
          >
            Go to your account
          </Link>
        )}
      </Card>
    </PageShell>
  );
}
