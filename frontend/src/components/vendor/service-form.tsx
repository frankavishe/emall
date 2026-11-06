"use client";

import { useState } from "react";
import { errorMessage, listCategories, type VendorServiceInput } from "@/lib/api-client";
import { useApi } from "@/lib/use-api";
import { CategoryOptions } from "@/components/category-options";
import { Button } from "@/components/ui/button";
import { FormField, inputClassName } from "@/components/ui/form-field";
import { ErrorText } from "@/components/ui/status-text";

const STEP_MINUTES = 30;
const MAX_MINUTES = 24 * 60;

/** Fields shared by creating and editing a service. `shopField` is the shop picker on create. */
export function ServiceForm({
  initial,
  submitLabel,
  shopField,
  onSubmit,
}: {
  initial?: VendorServiceInput;
  submitLabel: string;
  shopField?: React.ReactNode;
  onSubmit: (data: VendorServiceInput) => Promise<void>;
}) {
  const categories = useApi(() => listCategories("SERVICE"), "service-categories", true);
  const [name, setName] = useState(initial?.name ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [price, setPrice] = useState(initial?.price ?? "");
  const [duration, setDuration] = useState(String(initial?.duration_minutes ?? 60));
  const [category, setCategory] = useState(initial?.category ?? "");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await onSubmit({
        name,
        description,
        price,
        duration_minutes: Number(duration),
        category,
      });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  }

  const noCategories = categories.data !== null && categories.data.length === 0;

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      {shopField}
      <FormField label="Name">
        <input
          type="text"
          required
          maxLength={255}
          value={name}
          onChange={(e) => setName(e.target.value)}
          className={inputClassName}
        />
      </FormField>
      <FormField label="Description">
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className={inputClassName}
        />
      </FormField>
      <FormField label="Price (TZS)">
        <input
          type="number"
          required
          min="1"
          step="1"
          value={price}
          onChange={(e) => setPrice(e.target.value)}
          className={inputClassName}
        />
      </FormField>
      <FormField label="Duration (minutes)">
        <input
          type="number"
          required
          min={STEP_MINUTES}
          max={MAX_MINUTES}
          step={STEP_MINUTES}
          value={duration}
          onChange={(e) => setDuration(e.target.value)}
          className={inputClassName}
        />
      </FormField>
      <FormField label="Category">
        <select
          required
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className={inputClassName}
        >
          <option value="">Choose a category</option>
          <CategoryOptions categories={categories.data ?? []} />
        </select>
      </FormField>
      {noCategories && (
        <p className="text-sm text-text-muted">
          No service categories exist yet. An administrator needs to add one first.
        </p>
      )}
      {error && <ErrorText>{error}</ErrorText>}
      <Button type="submit" disabled={isSubmitting} fullWidth className="mt-2">
        {isSubmitting ? "Saving…" : submitLabel}
      </Button>
    </form>
  );
}
