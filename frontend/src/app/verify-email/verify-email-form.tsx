"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { apiFetch, ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

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
    <main className="mx-auto flex min-h-screen max-w-sm flex-col justify-center px-6 py-12">
      <h1 className="mb-6 text-2xl font-semibold">Email verification</h1>
      <p className={`text-sm ${status === "error" ? "text-red-600" : "text-black/80"}`}>
        {message}
      </p>

      {status === "error" && user && (
        <div className="mt-6">
          <button
            type="button"
            onClick={handleResend}
            disabled={isResending}
            className="rounded-md border border-black/15 px-4 py-2 text-sm font-medium disabled:opacity-50"
          >
            {isResending ? "Sending…" : "Resend verification email"}
          </button>
          {resendMessage && <p className="mt-2 text-sm text-black/60">{resendMessage}</p>}
        </div>
      )}

      {status === "success" && (
        <a href="/account" className="mt-6 text-sm underline">
          Go to your account
        </a>
      )}
    </main>
  );
}
