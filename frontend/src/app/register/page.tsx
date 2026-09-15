"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { ApiError } from "@/lib/api-client";

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
      router.push("/account");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-sm flex-col justify-center px-6 py-12">
      <h1 className="mb-6 text-2xl font-semibold">Create your account</h1>
      <div className="mb-4 flex gap-2 text-sm font-medium">
        <button
          type="button"
          onClick={() => setAccountType("customer")}
          className={`rounded-md border px-3 py-1.5 ${
            accountType === "customer" ? "border-black bg-black text-white" : "border-black/15"
          }`}
        >
          Customer
        </button>
        <button
          type="button"
          onClick={() => setAccountType("vendor")}
          className={`rounded-md border px-3 py-1.5 ${
            accountType === "vendor" ? "border-black bg-black text-white" : "border-black/15"
          }`}
        >
          Vendor
        </button>
      </div>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <label className="flex flex-col gap-1 text-sm font-medium">
          Name
          <input
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="rounded-md border border-black/15 px-3 py-2 text-base outline-none focus:border-black/40"
          />
        </label>
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
        <label className="flex flex-col gap-1 text-sm font-medium">
          Password
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="rounded-md border border-black/15 px-3 py-2 text-base outline-none focus:border-black/40"
          />
        </label>
        {accountType === "vendor" && (
          <label className="flex flex-col gap-1 text-sm font-medium">
            Shop name
            <input
              type="text"
              required
              value={shopName}
              onChange={(e) => setShopName(e.target.value)}
              className="rounded-md border border-black/15 px-3 py-2 text-base outline-none focus:border-black/40"
            />
          </label>
        )}
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={isSubmitting}
          className="mt-2 rounded-md bg-black px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {isSubmitting ? "Creating account…" : "Create account"}
        </button>
      </form>
      <p className="mt-6 text-sm text-black/60">
        Already have an account?{" "}
        <a href="/login" className="underline">
          Log in
        </a>
      </p>
    </main>
  );
}
