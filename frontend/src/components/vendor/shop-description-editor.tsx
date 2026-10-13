"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { FormField, inputClassName } from "@/components/ui/form-field";
import { ErrorText } from "@/components/ui/status-text";
import {
  errorMessage,
  MAX_SHOP_DESCRIPTION_LENGTH,
  updateShopDescription,
} from "@/lib/api-client";
import { useAuth, type Shop } from "@/lib/auth-context";

const PLACEHOLDER =
  "Mama Neema Crafts brings handwoven baskets and kitenge fashion made by Arusha artisans, " +
  "with every piece sourced fairly. Shop baskets, bags, home décor and tailored outfits. " +
  "Featured at the Sabasaba trade fair. Browse our new arrivals today!";

/** Edit the blurb shown on the shop's public storefront. Saves on demand, then refreshes the
 * profile so `user.shops` carries the new text. */
export function ShopDescriptionEditor({ shop }: { shop: Shop }) {
  const { refreshUser } = useAuth();
  const saved = shop.description ?? "";
  const [description, setDescription] = useState(saved);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const isDirty = description.trim() !== saved;

  async function save() {
    setError(null);
    setIsSaving(true);
    try {
      await updateShopDescription(shop.id, description.trim());
      await refreshUser();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <FormField label="Shop description">
        <textarea
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          rows={6}
          maxLength={MAX_SHOP_DESCRIPTION_LENGTH}
          placeholder={PLACEHOLDER}
          className={inputClassName}
        />
      </FormField>
      <div className="flex items-start justify-between gap-3 text-xs text-text-muted">
        <p>
          Introduce your shop in a few sentences: what you sell and what you stand for, your main
          product categories, anything notable (awards, years in business, handmade, local
          sourcing…), and an invitation for shoppers to browse.
        </p>
        <span className="shrink-0 tabular-nums">
          {description.length}/{MAX_SHOP_DESCRIPTION_LENGTH}
        </span>
      </div>
      <div>
        <Button size="sm" disabled={isSaving || !isDirty} onClick={() => void save()}>
          {isSaving ? "Saving…" : "Save description"}
        </Button>
      </div>
      {error && <ErrorText>{error}</ErrorText>}
    </div>
  );
}
