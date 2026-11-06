"use client";

import { useState } from "react";
import { listCategories, listServices } from "@/lib/api-client";
import { useApi } from "@/lib/use-api";
import { CategoryOptions } from "@/components/category-options";
import { Pager } from "@/components/pager";
import { ServiceCard } from "@/components/booking/service-card";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { FormField, inputClassName } from "@/components/ui/form-field";
import { EmptyText, ErrorText, LoadingText } from "@/components/ui/status-text";

export function ServiceCatalog({ initialCategory = "" }: { initialCategory?: string }) {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState(initialCategory);
  const [applied, setApplied] = useState({ search: "", category: initialCategory });
  const [page, setPage] = useState(1);

  const categories = useApi(() => listCategories("SERVICE"), "service-categories", true);
  const services = useApi(
    () => listServices({ ...applied, page }),
    `${applied.search}|${applied.category}|${page}`,
    true,
  );

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setApplied({ search, category });
    setPage(1);
  }

  const results = services.data?.results ?? [];

  return (
    <div className="flex flex-col gap-6">
      <Card as="form" onSubmit={handleSubmit} className="flex flex-wrap items-end gap-3">
        <FormField label="Search">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Haircut, oil change…"
            className={inputClassName}
          />
        </FormField>
        <FormField label="Category">
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className={inputClassName}
          >
            <option value="">All categories</option>
            <CategoryOptions categories={categories.data ?? []} selectableParents />
          </select>
        </FormField>
        <Button type="submit">Apply filters</Button>
      </Card>

      {services.error && <ErrorText>{services.error}</ErrorText>}

      {services.isLoading && !services.data ? (
        <LoadingText>Loading services…</LoadingText>
      ) : services.error ? null : results.length === 0 ? (
        <EmptyText>No services match your search.</EmptyText>
      ) : (
        <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3">
          {results.map((service) => (
            <ServiceCard key={service.id} service={service} />
          ))}
        </ul>
      )}

      <Pager
        previous={services.data?.previous ?? null}
        next={services.data?.next ?? null}
        onPrevious={() => setPage((current) => current - 1)}
        onNext={() => setPage((current) => current + 1)}
      />
    </div>
  );
}
