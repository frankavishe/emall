"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { ErrorText } from "@/components/ui/status-text";
import { LocationPicker } from "@/components/location-picker";
import { PlaceSearch } from "@/components/place-search";
import { errorMessage, type LatLng, type ShopLocation } from "@/lib/api-client";
import { reverseGeocode, sameLatLng, toLatLng, type Place } from "@/lib/geo";

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
  // Whether the owner typed the address this session; if not, a pin dropped on the map (or
  // found by GPS) fills it in with the place's name, replacing any previously saved text.
  const addressTypedRef = useRef(false);
  const reverseRef = useRef<AbortController | null>(null);

  useEffect(() => () => reverseRef.current?.abort(), []);

  /** A pin from tapping/dragging the map or "Use my location". */
  function changePinFromMap(next: LatLng) {
    setPin(next);
    reverseRef.current?.abort();
    if (addressTypedRef.current) return;
    const controller = new AbortController();
    reverseRef.current = controller;
    reverseGeocode(next, controller.signal)
      .then((label) => {
        if (label && !controller.signal.aborted && !addressTypedRef.current) {
          setAddressText(label);
        }
      })
      .catch(() => {});
  }

  function selectPlace(place: Place) {
    reverseRef.current?.abort();
    addressTypedRef.current = false;
    setAddressText(place.label);
    setPin(place.pin);
  }

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
      <PlaceSearch
        label="Pickup address"
        value={addressText}
        onChange={(text) => {
          addressTypedRef.current = text.trim() !== "";
          setAddressText(text);
        }}
        onSelect={selectPlace}
      />
      <LocationPicker value={pin} onChange={changePinFromMap} label="Pickup location" />
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
