"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { FormField, inputClassName } from "@/components/ui/form-field";
import { ErrorText } from "@/components/ui/status-text";
import { LocationPicker } from "@/components/location-picker";
import { errorMessage, type LatLng, type ShopLocation } from "@/lib/api-client";
import { sameLatLng, toLatLng } from "@/lib/geo";

/** Edit a shop's pickup location: the pin delivery fees are measured from, plus a typed address
 * for riders. Used by the shop owner (account page) and by Administrators (shop detail). */
export function ShopLocationEditor({
  latitude,
  longitude,
  address,
  onSave,
  ownerView = false,
}: {
  latitude: string | null | undefined;
  longitude: string | null | undefined;
  address: string | undefined;
  onSave: (location: ShopLocation) => Promise<void>;
  /** Show the shop owner why the location matters. */
  ownerView?: boolean;
}) {
  const saved = toLatLng(latitude, longitude);
  const [pin, setPin] = useState<LatLng | null>(saved);
  const [addressText, setAddressText] = useState(address ?? "");
  const [error, setError] = useState<string | null>(null);
  const [savedMessage, setSavedMessage] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const isDirty =
    addressText.trim() !== (address ?? "") ||
    (pin !== null && (saved === null || !sameLatLng(pin, saved)));

  async function save() {
    if (!pin) return;
    setError(null);
    setSavedMessage(null);
    setIsSaving(true);
    try {
      await onSave({ ...pin, location_address: addressText.trim() });
      setSavedMessage("Location saved.");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      {ownerView && !saved && (
        <div
          role="alert"
          className="rounded-control border border-status-pending/40 bg-status-pending/10 p-3 text-sm text-text-primary"
        >
          <strong>Set your shop location.</strong> Customers can&apos;t check out your products
          until you do, because the delivery fee is measured from here.
        </div>
      )}
      <FormField label="Pickup address">
        <input
          type="text"
          value={addressText}
          onChange={(e) => setAddressText(e.target.value)}
          placeholder="e.g. Shop 14, Kariakoo Market, Dar es Salaam"
          className={inputClassName}
          maxLength={255}
        />
      </FormField>
      <LocationPicker value={pin} onChange={setPin} label="Pickup location" />
      {error && <ErrorText>{error}</ErrorText>}
      {savedMessage && !isDirty && <p className="text-sm text-text-muted">{savedMessage}</p>}
      <div>
        <Button
          size="sm"
          onClick={save}
          disabled={!pin || !addressText.trim() || !isDirty || isSaving}
        >
          {isSaving ? "Saving…" : "Save location"}
        </Button>
      </div>
    </div>
  );
}
