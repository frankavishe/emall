"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { apiFetch, listAdminShops, ApiError, type AdminShop } from "@/lib/api-client";

type StatusFilter = "" | "PENDING" | "APPROVED" | "REJECTED";

export default function AdminShopsPage() {
  const router = useRouter();
  const { user, isLoading } = useAuth();
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("PENDING");
  const [shops, setShops] = useState<AdminShop[]>([]);
  const [isLoadingShops, setIsLoadingShops] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pendingActionId, setPendingActionId] = useState<string | null>(null);
  const [rejectReasons, setRejectReasons] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!isLoading && (!user || user.role !== "ADMINISTRATOR")) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  const loadShops = useCallback(async (status: StatusFilter) => {
    setIsLoadingShops(true);
    setError(null);
    try {
      const response = await listAdminShops(status || undefined);
      setShops(response.results);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setIsLoadingShops(false);
    }
  }, []);

  useEffect(() => {
    if (user?.role !== "ADMINISTRATOR") return;
    let cancelled = false;

    async function run() {
      setIsLoadingShops(true);
      setError(null);
      try {
        const response = await listAdminShops(statusFilter || undefined);
        if (!cancelled) setShops(response.results);
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof ApiError ? err.message : "Something went wrong. Please try again.",
          );
        }
      } finally {
        if (!cancelled) setIsLoadingShops(false);
      }
    }

    void run();
    return () => {
      cancelled = true;
    };
  }, [user, statusFilter]);

  async function handleApprove(shopId: string) {
    setPendingActionId(shopId);
    setError(null);
    try {
      await apiFetch(`/api/admin/shops/${shopId}/approve`, { method: "POST" });
      await loadShops(statusFilter);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setPendingActionId(null);
    }
  }

  async function handleReject(shopId: string) {
    setPendingActionId(shopId);
    setError(null);
    try {
      const reason = rejectReasons[shopId]?.trim();
      await apiFetch(`/api/admin/shops/${shopId}/reject`, {
        method: "POST",
        body: JSON.stringify(reason ? { reason } : {}),
      });
      await loadShops(statusFilter);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setPendingActionId(null);
    }
  }

  if (isLoading || !user || user.role !== "ADMINISTRATOR") {
    return (
      <main className="mx-auto flex min-h-screen max-w-3xl items-center justify-center px-6">
        <p className="text-sm text-black/60">Loading…</p>
      </main>
    );
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col px-6 py-12">
      <h1 className="mb-6 text-2xl font-semibold">Shop approvals</h1>

      <div className="mb-6 flex gap-2">
        {(["PENDING", "APPROVED", "REJECTED", ""] as StatusFilter[]).map((option) => (
          <button
            key={option || "ALL"}
            type="button"
            onClick={() => setStatusFilter(option)}
            className={`rounded-md border px-3 py-1.5 text-sm font-medium ${
              statusFilter === option
                ? "border-black bg-black text-white"
                : "border-black/15 text-black/70"
            }`}
          >
            {option || "ALL"}
          </button>
        ))}
      </div>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

      {isLoadingShops ? (
        <p className="text-sm text-black/60">Loading shops…</p>
      ) : shops.length === 0 ? (
        <p className="text-sm text-black/60">No shops match this filter.</p>
      ) : (
        <ul className="flex flex-col gap-4">
          {shops.map((shop) => (
            <li key={shop.id} className="rounded-md border border-black/15 p-4">
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-medium">{shop.name}</p>
                  <p className="text-sm text-black/60">
                    {shop.owner_name} &middot; {shop.owner_email}
                  </p>
                  <p className="mt-1 text-sm text-black/60">Status: {shop.status}</p>
                  {shop.status_reason && (
                    <p className="mt-1 text-sm text-black/60">Reason: {shop.status_reason}</p>
                  )}
                </div>

                {shop.status === "PENDING" && (
                  <div className="flex flex-col items-end gap-2">
                    <button
                      type="button"
                      disabled={pendingActionId === shop.id}
                      onClick={() => handleApprove(shop.id)}
                      className="rounded-md border border-black/15 px-3 py-1.5 text-sm font-medium disabled:opacity-50"
                    >
                      Approve
                    </button>
                    <input
                      type="text"
                      placeholder="Reason (optional)"
                      value={rejectReasons[shop.id] ?? ""}
                      onChange={(e) =>
                        setRejectReasons((prev) => ({ ...prev, [shop.id]: e.target.value }))
                      }
                      className="rounded-md border border-black/15 px-2 py-1 text-sm outline-none focus:border-black/40"
                    />
                    <button
                      type="button"
                      disabled={pendingActionId === shop.id}
                      onClick={() => handleReject(shop.id)}
                      className="rounded-md border border-black/15 px-3 py-1.5 text-sm font-medium disabled:opacity-50"
                    >
                      Reject
                    </button>
                  </div>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
