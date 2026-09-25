"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { apiFetch, listAdminShops, ApiError, type AdminShop } from "@/lib/api-client";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Pill, statusToTone } from "@/components/ui/pill";
import { SegmentedToggle } from "@/components/ui/segmented-toggle";
import { ErrorText, LoadingText, EmptyText } from "@/components/ui/status-text";
import { inputClassName } from "@/components/ui/form-field";

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
      <PageShell size="md" className="min-h-screen items-center justify-center">
        <LoadingText />
      </PageShell>
    );
  }

  return (
    <PageShell size="md" title="Shop approvals">
      <SegmentedToggle
        options={[
          { value: "PENDING", label: "PENDING" },
          { value: "APPROVED", label: "APPROVED" },
          { value: "REJECTED", label: "REJECTED" },
          { value: "", label: "ALL" },
        ]}
        value={statusFilter}
        onChange={setStatusFilter}
        className="self-start"
      />

      {error && <ErrorText>{error}</ErrorText>}

      {isLoadingShops ? (
        <LoadingText>Loading shops…</LoadingText>
      ) : shops.length === 0 ? (
        <EmptyText>No shops match this filter.</EmptyText>
      ) : (
        <ul className="flex flex-col gap-4">
          {shops.map((shop) => (
            <Card as="li" key={shop.id} padding="sm">
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-medium text-text-primary">{shop.name}</p>
                  <p className="text-sm text-text-muted">
                    {shop.owner_name} &middot; {shop.owner_email}
                  </p>
                  <div className="mt-1">
                    <Pill tone={statusToTone(shop.status)}>{shop.status}</Pill>
                  </div>
                  {shop.status_reason && (
                    <p className="mt-1 text-sm text-text-muted">Reason: {shop.status_reason}</p>
                  )}
                </div>

                {shop.status === "PENDING" && (
                  <div className="flex flex-col items-end gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      disabled={pendingActionId === shop.id}
                      onClick={() => handleApprove(shop.id)}
                    >
                      Approve
                    </Button>
                    <input
                      type="text"
                      placeholder="Reason (optional)"
                      value={rejectReasons[shop.id] ?? ""}
                      onChange={(e) =>
                        setRejectReasons((prev) => ({ ...prev, [shop.id]: e.target.value }))
                      }
                      className={`text-sm ${inputClassName}`}
                    />
                    <Button
                      variant="danger"
                      size="sm"
                      disabled={pendingActionId === shop.id}
                      onClick={() => handleReject(shop.id)}
                    >
                      Reject
                    </Button>
                  </div>
                )}
              </div>
            </Card>
          ))}
        </ul>
      )}
    </PageShell>
  );
}
