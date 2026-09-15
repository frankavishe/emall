"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { ApiError } from "@/lib/api-client";

export default function AccountPage() {
  const router = useRouter();
  const { user, isLoading, logout, requestShop } = useAuth();
  const [newShopName, setNewShopName] = useState("");
  const [shopError, setShopError] = useState<string | null>(null);
  const [isRequestingShop, setIsRequestingShop] = useState(false);

  useEffect(() => {
    if (!isLoading && !user) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  async function handleLogout() {
    await logout();
    router.push("/login");
  }

  async function handleRequestShop(event: React.FormEvent) {
    event.preventDefault();
    setShopError(null);
    setIsRequestingShop(true);
    try {
      await requestShop(newShopName);
      setNewShopName("");
    } catch (err) {
      setShopError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setIsRequestingShop(false);
    }
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

      {user.role === "VENDOR" && (
        <section className="mt-8">
          <h2 className="mb-3 text-lg font-semibold">Your shops</h2>
          <ul className="flex flex-col gap-2 text-sm">
            {(user.shops ?? []).map((shop) => (
              <li key={shop.id} className="flex justify-between">
                <span className="font-medium">{shop.name}</span>
                <span className="text-black/60">{shop.status}</span>
              </li>
            ))}
            {(user.shops ?? []).length === 0 && (
              <li className="text-black/60">No shops yet.</li>
            )}
          </ul>
          <form onSubmit={handleRequestShop} className="mt-4 flex flex-col gap-2">
            <label className="flex flex-col gap-1 text-sm font-medium">
              Request another shop
              <input
                type="text"
                required
                value={newShopName}
                onChange={(e) => setNewShopName(e.target.value)}
                className="rounded-md border border-black/15 px-3 py-2 text-base outline-none focus:border-black/40"
              />
            </label>
            {shopError && <p className="text-sm text-red-600">{shopError}</p>}
            <button
              type="submit"
              disabled={isRequestingShop}
              className="rounded-md border border-black/15 px-4 py-2 text-sm font-medium disabled:opacity-50"
            >
              {isRequestingShop ? "Requesting…" : "Request shop"}
            </button>
          </form>
        </section>
      )}

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
