"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { createVendorService } from "@/lib/api-client";
import { useRequireRole } from "@/lib/use-api";
import { ServiceForm } from "@/components/vendor/service-form";
import { Card } from "@/components/ui/card";
import { FormField, inputClassName } from "@/components/ui/form-field";
import { PageShell } from "@/components/ui/page-shell";
import { LoadingText } from "@/components/ui/status-text";

export default function NewVendorServicePage() {
  const router = useRouter();
  const allowed = useRequireRole("VENDOR");
  const { user } = useAuth();
  const [shopId, setShopId] = useState("");

  if (!allowed) {
    return (
      <PageShell size="sm" className="min-h-screen items-center justify-center">
        <LoadingText />
      </PageShell>
    );
  }

  const shops = (user?.shops ?? []).filter(
    (shop) => shop.status === "APPROVED" && shop.business_type === "SERVICES",
  );

  if (shops.length === 0) {
    return (
      <PageShell size="sm" className="min-h-screen justify-center">
        <Card>
          <h1 className="mb-4 text-2xl font-semibold text-text-primary">New service</h1>
          <p className="text-sm text-text-muted">
            You need an approved services shop before you can add a service. You can request one
            from your account page.
          </p>
        </Card>
      </PageShell>
    );
  }

  const effectiveShopId = shopId || String(shops[0].id);

  return (
    <PageShell size="md">
      <Card>
        <h1 className="mb-6 text-2xl font-semibold text-text-primary">New service</h1>
        <ServiceForm
          submitLabel="Create service"
          shopField={
            <FormField label="Shop">
              <select
                required
                value={effectiveShopId}
                onChange={(e) => setShopId(e.target.value)}
                className={inputClassName}
              >
                {shops.map((shop) => (
                  <option key={shop.id} value={shop.id}>
                    {shop.name}
                  </option>
                ))}
              </select>
            </FormField>
          }
          onSubmit={async (data) => {
            await createVendorService({ ...data, shop_id: Number(effectiveShopId) });
            router.push("/vendor/services");
          }}
        />
      </Card>
    </PageShell>
  );
}
