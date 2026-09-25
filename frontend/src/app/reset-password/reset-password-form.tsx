"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { apiFetch, ApiError } from "@/lib/api-client";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FormField, inputClassName } from "@/components/ui/form-field";
import { ErrorText } from "@/components/ui/status-text";

export default function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    if (!token) {
      setError("This reset link is missing a token.");
      return;
    }

    setIsSubmitting(true);
    try {
      await apiFetch("/api/auth/password-reset/confirm", {
        method: "POST",
        body: JSON.stringify({ token, new_password: newPassword }),
      });
      router.push("/login");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <PageShell size="sm" className="min-h-screen justify-center">
      <Card>
        <h1 className="mb-6 text-2xl font-semibold text-text-primary">Set a new password</h1>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <FormField label="New password">
            <input
              type="password"
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
      </Card>
    </PageShell>
  );
}
