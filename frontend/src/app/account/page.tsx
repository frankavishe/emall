"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

export default function AccountPage() {
  const router = useRouter();
  const { user, isLoading, logout } = useAuth();

  useEffect(() => {
    if (!isLoading && !user) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  async function handleLogout() {
    await logout();
    router.push("/login");
  }

  if (isLoading) {
    return (
      <main className="mx-auto flex min-h-screen max-w-sm items-center justify-center px-6">
        <p className="text-sm text-black/60">Loading…</p>
      </main>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-sm flex-col justify-center px-6 py-12">
      <h1 className="mb-6 text-2xl font-semibold">Your account</h1>
      <dl className="flex flex-col gap-3 text-sm">
        <div className="flex justify-between">
          <dt className="text-black/60">Name</dt>
          <dd className="font-medium">{user.name}</dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-black/60">Email</dt>
          <dd className="font-medium">{user.email}</dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-black/60">Role</dt>
          <dd className="font-medium">{user.role}</dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-black/60">Email verified</dt>
          <dd className="font-medium">{user.is_email_verified ? "Yes" : "No"}</dd>
        </div>
      </dl>
      <button
        type="button"
        onClick={handleLogout}
        className="mt-8 rounded-md border border-black/15 px-4 py-2 text-sm font-medium"
      >
        Log out
      </button>
    </main>
  );
}
