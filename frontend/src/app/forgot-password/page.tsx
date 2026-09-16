"use client";

import { useState } from "react";
import { apiFetch } from "@/lib/api-client";

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
    <main className="mx-auto flex min-h-screen max-w-sm flex-col justify-center px-6 py-12">
      <h1 className="mb-6 text-2xl font-semibold">Reset your password</h1>
      {submitted ? (
        <p className="text-sm text-black/80">{CONFIRMATION_MESSAGE}</p>
      ) : (
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <label className="flex flex-col gap-1 text-sm font-medium">
            Email
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="rounded-md border border-black/15 px-3 py-2 text-base outline-none focus:border-black/40"
            />
          </label>
          <button
            type="submit"
            disabled={isSubmitting}
            className="mt-2 rounded-md bg-black px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {isSubmitting ? "Sending…" : "Send reset link"}
          </button>
        </form>
      )}
      <p className="mt-6 text-sm text-black/60">
        Remembered your password?{" "}
        <a href="/login" className="underline">
          Log in
        </a>
      </p>
    </main>
  );
}
