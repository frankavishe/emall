import type { Metadata } from "next";
import { SearchResults } from "@/components/search-results";
import { PageShell } from "@/components/ui/page-shell";

export const metadata: Metadata = { title: "Search" };

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const { q } = await searchParams;
  const query = typeof q === "string" ? q.trim() : "";

  return (
    <PageShell size="xl" title={query ? `Results for “${query}”` : "Search"}>
      {/* Keyed so a new search starts fresh. */}
      <SearchResults key={query} query={query} />
    </PageShell>
  );
}
