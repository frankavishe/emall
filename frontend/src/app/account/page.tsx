"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { hasRole, useAuth, type Shop } from "@/lib/auth-context";
import { errorMessage, updateShopLocation } from "@/lib/api-client";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { inputClassName } from "@/components/ui/form-field";
import { Pill, statusToTone } from "@/components/ui/pill";
import { ErrorText, LoadingText } from "@/components/ui/status-text";
import { ShopLogo } from "@/components/shop-logo";
import { AvatarPicker } from "@/components/account/avatar-picker";
import { PersonalInfoForm } from "@/components/account/personal-info-form";
import { ShopLogoPicker } from "@/components/vendor/shop-logo-picker";
import { ShopThemePicker } from "@/components/vendor/shop-theme-picker";
import { ShopDescriptionEditor } from "@/components/vendor/shop-description-editor";
import { ShopNameEditor } from "@/components/vendor/shop-name-editor";
import { ShopLocationEditor } from "@/components/vendor/shop-location-editor";

// Shown under a shop's header while it can't sell yet.
const STATUS_NOTES: Record<string, string> = {
  PENDING: "Awaiting admin approval. You can set the shop up now; it goes live once approved.",
  REJECTED: "This shop was not approved. Contact support if you think this is a mistake.",
};

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

  const isVendor = hasRole(user, "VENDOR");
  const shops = user.shops ?? [];

  const requestShopForm = (
    <form onSubmit={handleRequestShop} className="flex flex-col gap-2">
      <div className="flex flex-col gap-2 sm:flex-row">
        <input
          type="text"
          required
          value={newShopName}
          onChange={(e) => setNewShopName(e.target.value)}
          placeholder="Shop name"
          aria-label="Shop name"
          className={`${inputClassName} sm:flex-1`}
        />
        <Button type="submit" disabled={isRequestingShop}>
          {isRequestingShop ? "Sending…" : isVendor ? "Request shop" : "Open a shop"}
        </Button>
      </div>
      {shopError && <ErrorText>{shopError}</ErrorText>}
    </form>
  );

  return (
    <PageShell
      size="md"
      title="Your account"
      description={
        isVendor ? "Manage your profile and how your shops look to buyers." : "Manage your profile."
      }
    >
      <Card className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <AvatarPicker user={user} />
        <div className="flex flex-col gap-2 sm:items-end">
          <p className="text-lg font-semibold text-text-primary">{user.name}</p>
          <div className="flex flex-wrap gap-2">
            {user.roles.map((role) => (
              <Pill key={role} tone="neutral">
                <span className="capitalize">{role.toLowerCase()}</span>
              </Pill>
            ))}
            {user.is_email_verified ? (
              <Pill tone="approved">Email verified</Pill>
            ) : (
              <Link href="/verify-email">
                <Pill tone="pending">Verify your email →</Pill>
              </Link>
            )}
          </div>
          <Button variant="ghost" size="sm" onClick={handleLogout} className="sm:-mr-3">
            Log out
          </Button>
        </div>
      </Card>

      <Card className="flex flex-col gap-4">
        <h2 className="text-lg font-semibold text-text-primary">Personal information</h2>
        <PersonalInfoForm key={user.id} user={user} />
      </Card>

      {isVendor ? (
        <>
          {shops.map((shop) => (
            <ShopSettingsCard key={shop.id} shop={shop} />
          ))}
          {shops.length === 0 && (
            <Card variant="muted">
              <p className="text-sm text-text-muted">You don&apos;t have any shops yet.</p>
            </Card>
          )}
          <Card variant="muted" className="flex flex-col gap-3">
            <div className="flex flex-col gap-1">
              <h2 className="text-base font-semibold text-text-primary">Open another shop</h2>
              <p className="text-sm text-text-muted">
                Sell a different range under its own name. New shops are reviewed by an
                administrator before they go live.
              </p>
            </div>
            {requestShopForm}
          </Card>
        </>
      ) : (
        hasRole(user, "CUSTOMER") && (
          <Card className="flex flex-col gap-3">
            <div className="flex flex-col gap-1">
              <h2 className="text-lg font-semibold text-text-primary">Sell on E-Mall</h2>
              <p className="text-sm text-text-muted">
                Open a shop on this same account — you&apos;ll keep shopping as a customer too.
                New shops are reviewed by an administrator before you can sell.
              </p>
            </div>
            {requestShopForm}
          </Card>
        )
      )}
    </PageShell>
  );
}

/** Every editable setting of one shop, grouped into titled sections. */
function ShopSettingsCard({ shop }: { shop: Shop }) {
  const { refreshUser } = useAuth();
  const note = STATUS_NOTES[shop.status];

  return (
    <Card className="flex flex-col gap-6">
      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <ShopLogo url={shop.logo_url} name={shop.name} size="md" />
          <div className="flex min-w-0 flex-1 flex-col">
            <h2 className="truncate text-lg font-semibold text-text-primary">{shop.name}</h2>
            <span className="text-xs text-text-muted">Shop settings</span>
          </div>
          <Pill tone={statusToTone(shop.status)}>
            <span className="capitalize">{shop.status.toLowerCase()}</span>
          </Pill>
          {shop.status === "APPROVED" && (
            <Button asChild variant="secondary" size="sm">
              <Link href={`/shops/${shop.id}`}>View shop</Link>
            </Button>
          )}
        </div>
        {note && <p className="text-sm text-text-muted">{note}</p>}
      </div>

      <Section title="Shop details" hint="The name and introduction buyers see on your shop page.">
        <ShopNameEditor shop={shop} />
        <ShopDescriptionEditor shop={shop} />
      </Section>

      <Section title="Branding" hint="Your logo and colors theme your shop page and product cards.">
        <ShopLogoPicker shop={shop} />
        <ShopThemePicker shop={shop} />
      </Section>

      <Section
        title="Pickup & delivery"
        hint="Where riders collect orders. Delivery fees are calculated from this pin."
      >
        <ShopLocationEditor
          ownerView
          latitude={shop.latitude}
          longitude={shop.longitude}
          address={shop.location_address}
          onSave={async (location) => {
            await updateShopLocation(shop.id, location);
            await refreshUser();
          }}
        />
      </Section>
    </Card>
  );
}

function Section({
  title,
  hint,
  children,
}: {
  title: string;
  hint: string;
  children: React.ReactNode;
}) {
  return (
    <section className="flex flex-col gap-4 border-t border-border pt-6">
      <div className="flex flex-col gap-1">
        <h3 className="text-base font-semibold text-text-primary">{title}</h3>
        <p className="text-sm text-text-muted">{hint}</p>
      </div>
      {children}
    </section>
  );
}
