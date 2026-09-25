"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { ApiError } from "@/lib/api-client";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FormField, inputClassName } from "@/components/ui/form-field";
import { ErrorText } from "@/components/ui/status-text";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await login(email, password);
      router.push("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <PageShell size="sm" className="min-h-screen justify-center">
      <Card>
        <h1 className="mb-6 text-2xl font-semibold text-text-primary">Log in</h1>
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
          <FormField label="Password">
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={inputClassName}
            />
          </FormField>
          {error && <ErrorText>{error}</ErrorText>}
          <Button type="submit" disabled={isSubmitting} fullWidth className="mt-2">
            {isSubmitting ? "Logging in…" : "Log in"}
          </Button>
        </form>
        <p className="mt-6 text-sm text-text-muted">
          Need an account?{" "}
          <Link href="/register" className="font-medium text-navy-900 underline">
            Register
          </Link>
        </p>
        <p className="mt-2 text-sm text-text-muted">
          <Link href="/forgot-password" className="font-medium text-navy-900 underline">
            Forgot your password?
          </Link>
        </p>
      </Card>
    </PageShell>
  );
}
