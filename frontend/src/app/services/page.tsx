import { ServiceCatalog } from "@/components/booking/service-catalog";
import { PageShell } from "@/components/ui/page-shell";

export default async function ServicesPage({
  searchParams,
}: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const { category } = await searchParams;
  const initialCategory = typeof category === "string" ? category : "";

  return (
    <PageShell
      size="xl"
      title="Services"
      description="Find a salon, clinic, garage or other business, and see when it's open."
    >
      {/* Keyed so following a different ?category= link resets the filters. */}
      <ServiceCatalog key={initialCategory} initialCategory={initialCategory} />
    </PageShell>
  );
}
