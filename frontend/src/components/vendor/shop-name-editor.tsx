"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { FormField, inputClassName } from "@/components/ui/form-field";
import { ErrorText } from "@/components/ui/status-text";
import { errorMessage, updateShopName } from "@/lib/api-client";
import { useAuth, type Shop } from "@/lib/auth-context";

/** Rename a shop. Saves on demand, then refreshes the profile so `user.shops` carries the new
 * name. */
export function ShopNameEditor({ shop }: { shop: Shop }) {
  const { refreshUser } = useAuth();
  const [name, setName] = useState(shop.name);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const trimmed = name.trim();
  const isDirty = trimmed !== "" && trimmed !== shop.name;

  async function save() {
    setError(null);
    setIsSaving(true);
    try {
      await updateShopName(shop.id, trimmed);
      await refreshUser();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <FormField label="Shop name">
        <input
          type="text"
          required
          value={name}
          onChange={(event) => setName(event.target.value)}
          maxLength={255}
          className={inputClassName}
        />
      </FormField>
      <div>
        <Button size="sm" disabled={isSaving || !isDirty} onClick={() => void save()}>
          {isSaving ? "Saving…" : "Save name"}
        </Button>
      </div>
      {error && <ErrorText>{error}</ErrorText>}
    </div>
  );
}
