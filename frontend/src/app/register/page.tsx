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
import { SegmentedToggle } from "@/components/ui/segmented-toggle";

type AccountType = "customer" | "vendor";

export default function RegisterPage() {
  const router = useRouter();
  const { registerCustomer, registerVendor } = useAuth();
  const [accountType, setAccountType] = useState<AccountType>("customer");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [shopName, setShopName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      if (accountType === "vendor") {
        await registerVendor(name, email, password, shopName);
      } else {
        await registerCustomer(name, email, password);
      }
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
        <h1 className="mb-6 text-2xl font-semibold text-text-primary">Create your account</h1>
        <SegmentedToggle
          className="mb-4"
          options={[
            { value: "customer", label: "Customer" },
            { value: "vendor", label: "Vendor" },
          ]}
          value={accountType}
          onChange={setAccountType}
        />
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <FormField label="Name">
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className={inputClassName}
            />
          </FormField>
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
          {accountType === "vendor" && (
            <FormField label="Shop name">
              <input
                type="text"
                required
                value={shopName}
                onChange={(e) => setShopName(e.target.value)}
                className={inputClassName}
              />
            </FormField>
          )}
          {error && <ErrorText>{error}</ErrorText>}
          <Button type="submit" disabled={isSubmitting} fullWidth className="mt-2">
            {isSubmitting ? "Creating account…" : "Create account"}
          </Button>
        </form>
        <p className="mt-6 text-sm text-text-muted">
          Already have an account?{" "}
          <Link href="/login" className="font-medium text-navy-900 underline">
            Log in
          </Link>
        </p>
      </Card>
    </PageShell>
  );
}
