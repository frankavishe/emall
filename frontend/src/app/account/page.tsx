"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { hasRole, useAuth } from "@/lib/auth-context";
import { errorMessage } from "@/lib/api-client";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FormField, inputClassName } from "@/components/ui/form-field";
import { Pill, statusToTone } from "@/components/ui/pill";
import { ErrorText, LoadingText, EmptyText } from "@/components/ui/status-text";

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
      setShopError(errorMessage(err));
    } finally {
      setIsRequestingShop(false);
    }
  }

  if (isLoading) {
    return (
      <PageShell size="sm" className="min-h-screen items-center justify-center">
        <LoadingText />
      </PageShell>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <PageShell size="sm" className="min-h-screen justify-center">
      <Card>
        <h1 className="mb-6 text-2xl font-semibold text-text-primary">Your account</h1>
        <dl className="flex flex-col gap-3 text-sm">
          <div className="flex justify-between">
            <dt className="text-text-muted">Name</dt>
            <dd className="font-medium text-text-primary">{user.name}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-text-muted">Email</dt>
            <dd className="font-medium text-text-primary">{user.email}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-text-muted">{user.roles.length > 1 ? "Roles" : "Role"}</dt>
            <dd className="font-medium capitalize text-text-primary">
              {user.roles.map((role) => role.toLowerCase()).join(" · ")}
            </dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-text-muted">Email verified</dt>
            <dd className="font-medium text-text-primary">
              {user.is_email_verified ? (
                "Yes"
              ) : (
                <>
                  No ·{" "}
                  <Link href="/verify-email" className="text-navy-900 underline">
                    Verify now
                  </Link>
                </>
              )}
            </dd>
          </div>
        </dl>

        {hasRole(user, "CUSTOMER") && !hasRole(user, "VENDOR") && (
          <section className="mt-8">
            <h2 className="mb-1 text-lg font-semibold text-text-primary">Sell on E-Mall</h2>
            <p className="mb-3 text-sm text-text-muted">
              Open a shop on this same account — you&apos;ll keep shopping as a customer too. New
              shops are reviewed by an administrator before you can sell.
            </p>
            <form onSubmit={handleRequestShop} className="flex flex-col gap-2">
              <FormField label="Shop name">
                <input
                  type="text"
                  required
                  value={newShopName}
                  onChange={(e) => setNewShopName(e.target.value)}
                  className={inputClassName}
                />
              </FormField>
              {shopError && <ErrorText>{shopError}</ErrorText>}
              <Button type="submit" variant="secondary" disabled={isRequestingShop}>
                {isRequestingShop ? "Opening…" : "Open a shop"}
              </Button>
            </form>
          </section>
        )}

        {hasRole(user, "VENDOR") && (
          <section className="mt-8">
            <h2 className="mb-3 text-lg font-semibold text-text-primary">Your shops</h2>
            <ul className="flex flex-col gap-2 text-sm">
              {(user.shops ?? []).map((shop) => (
                <li key={shop.id} className="flex items-center justify-between">
                  <span className="font-medium text-text-primary">{shop.name}</span>
                  <Pill tone={statusToTone(shop.status)}>{shop.status}</Pill>
                </li>
              ))}
              {(user.shops ?? []).length === 0 && <EmptyText>No shops yet.</EmptyText>}
            </ul>
            <form onSubmit={handleRequestShop} className="mt-4 flex flex-col gap-2">
              <FormField label="Request another shop">
                <input
                  type="text"
                  required
                  value={newShopName}
                  onChange={(e) => setNewShopName(e.target.value)}
                  className={inputClassName}
                />
              </FormField>
              {shopError && <ErrorText>{shopError}</ErrorText>}
              <Button type="submit" variant="secondary" disabled={isRequestingShop}>
                {isRequestingShop ? "Requesting…" : "Request shop"}
              </Button>
            </form>
          </section>
        )}

        <Button variant="secondary" onClick={handleLogout} className="mt-8">
          Log out
        </Button>
      </Card>
    </PageShell>
  );
}
