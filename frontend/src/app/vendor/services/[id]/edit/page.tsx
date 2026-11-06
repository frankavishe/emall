"use client";

import { useParams, useRouter } from "next/navigation";
import { getVendorService, updateVendorService } from "@/lib/api-client";
import { useApi, useRequireRole } from "@/lib/use-api";
import { ServiceForm } from "@/components/vendor/service-form";
import { Card } from "@/components/ui/card";
import { PageShell } from "@/components/ui/page-shell";
import { ErrorText, LoadingText } from "@/components/ui/status-text";

export default function EditVendorServicePage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const allowed = useRequireRole("VENDOR");
  const service = useApi(() => getVendorService(params.id), params.id, allowed);

  if (!allowed || (service.isLoading && !service.data)) {
    return (
      <PageShell size="md" className="min-h-screen items-center justify-center">
        <LoadingText />
      </PageShell>
    );
  }

  if (!service.data) {
    return (
      <PageShell size="md">
        <ErrorText>{service.error ?? "This service could not be found."}</ErrorText>
      </PageShell>
    );
  }

  return (
    <PageShell size="md">
      <Card>
        <h1 className="mb-6 text-2xl font-semibold text-text-primary">Edit service</h1>
        <ServiceForm
          initial={service.data}
          submitLabel="Save changes"
          onSubmit={async (data) => {
            await updateVendorService(params.id, data);
            router.push("/vendor/services");
          }}
        />
      </Card>
    </PageShell>
  );
}
