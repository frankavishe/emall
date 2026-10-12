import type { LatLng } from "./api-client";

/** Where the map opens when there's no pin yet: Dar es Salaam city centre. */
export const DEFAULT_CENTER: LatLng = { latitude: -6.7924, longitude: 39.2083 };

/** A pin from API decimal strings, or null if either coordinate is missing. */
export function toLatLng(
  latitude: string | number | null | undefined,
  longitude: string | number | null | undefined,
): LatLng | null {
  if (latitude === null || latitude === undefined || latitude === "") return null;
  if (longitude === null || longitude === undefined || longitude === "") return null;
  const lat = Number(latitude);
  const lng = Number(longitude);
  return Number.isFinite(lat) && Number.isFinite(lng) ? { latitude: lat, longitude: lng } : null;
}

/** A link that opens the spot in the device's maps app (or Google Maps on the web). */
export function mapsUrl(pin: LatLng): string {
  return `https://www.google.com/maps/search/?api=1&query=${pin.latitude},${pin.longitude}`;
}

export function formatLatLng(pin: LatLng): string {
  return `${pin.latitude.toFixed(5)}, ${pin.longitude.toFixed(5)}`;
}

/** The device's current position, or a user-facing error message on failure. */
export function requestCurrentPosition(timeoutMs = 15000): Promise<LatLng> {
  return new Promise((resolve, reject) => {
    if (typeof navigator === "undefined" || !navigator.geolocation) {
      reject(new Error("Your browser can't share your location. Drop the pin on the map instead."));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) =>
        resolve({ latitude: position.coords.latitude, longitude: position.coords.longitude }),
      (error) => {
        const messages: Record<number, string> = {
          1: "Location permission was denied. Allow it in your browser, or drop the pin on the map.",
          2: "Your location isn't available right now. Drop the pin on the map instead.",
          3: "Finding your location took too long. Try again, or drop the pin on the map.",
        };
        reject(new Error(messages[error.code] ?? messages[2]));
      },
      { enableHighAccuracy: true, timeout: timeoutMs, maximumAge: 60000 },
    );
  });
}
