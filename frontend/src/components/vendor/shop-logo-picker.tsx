"use client";

import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { ErrorText } from "@/components/ui/status-text";
import { ShopLogo } from "@/components/shop-logo";
import { errorMessage, removeShopLogo, uploadShopLogo } from "@/lib/api-client";
import { useAuth, type Shop } from "@/lib/auth-context";

// Mirrors MAX_SHOP_LOGO_SIZE_BYTES in backend/apps/vendors/serializers.py.
export const MAX_LOGO_SIZE_BYTES = 2 * 1024 * 1024;

/** Upload, replace or remove one shop's logo. Saves immediately, then refreshes the profile so
 * every place that reads `user.shops` picks up the new logo. */
export function ShopLogoPicker({ shop }: { shop: Shop }) {
  const { refreshUser } = useAuth();
  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  async function save(action: () => Promise<void>) {
    setError(null);
    setIsSaving(true);
    try {
      await action();
      await refreshUser();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setIsSaving(false);
    }
  }

  function handlePick(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    // Reset so picking the same file again still fires onChange.
    event.target.value = "";
    if (!file) return;
    if (file.size > MAX_LOGO_SIZE_BYTES) {
      setError(`${file.name} is over 2MB.`);
      return;
    }
    void save(() => uploadShopLogo(shop.id, file));
  }

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-3">
        <ShopLogo url={shop.logo_url} name={shop.name} size="md" />
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          onChange={handlePick}
          className="hidden"
        />
        <Button
          variant="secondary"
          size="sm"
          disabled={isSaving}
          onClick={() => inputRef.current?.click()}
        >
          {isSaving ? "Saving…" : shop.logo_url ? "Change logo" : "Upload logo"}
        </Button>
        {shop.logo_url && (
          <Button
            variant="ghost"
            size="sm"
            disabled={isSaving}
            onClick={() => save(() => removeShopLogo(shop.id))}
          >
            Remove
          </Button>
        )}
      </div>
      {error && <ErrorText>{error}</ErrorText>}
    </div>
  );
}
