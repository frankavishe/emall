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

/** Checkout only delivers within Dar es Salaam for now; place search is limited to this box
 * (west, south, east, north). */
export const DAR_ES_SALAAM_BBOX = [38.95, -7.25, 39.65, -6.55] as const;

// Photon: a free OpenStreetMap geocoder (no API key) built for search-as-you-type, which
// Nominatim's usage policy forbids.
const PHOTON_URL = "https://photon.komoot.io";

export type Place = { label: string; pin: LatLng };

type PhotonFeature = {
  geometry: { coordinates: [number, number] };
  properties: Record<string, string | undefined>;
};

/** A short, readable label for a geocoder result, e.g. "Kariakoo Market, Kariakoo, Ilala". */
function placeLabel(properties: PhotonFeature["properties"]): string {
  const street = [properties.housenumber, properties.street].filter(Boolean).join(" ");
  const parts = [
    properties.name,
    street,
    properties.locality,
    properties.district,
    properties.city ?? properties.county,
  ].filter((part): part is string => !!part);
  return [...new Set(parts)].join(", ");
}

function toPlaces(body: { features?: PhotonFeature[] }): Place[] {
  return (body.features ?? [])
    .map((feature) => ({
      label: placeLabel(feature.properties),
      pin: {
        latitude: feature.geometry.coordinates[1],
        longitude: feature.geometry.coordinates[0],
      },
    }))
    .filter((place) => place.label);
}

/** Places in Dar es Salaam matching what the customer typed. */
export async function searchPlaces(query: string, signal?: AbortSignal): Promise<Place[]> {
  const params = new URLSearchParams({
    q: query,
    bbox: DAR_ES_SALAAM_BBOX.join(","),
    limit: "5",
    lang: "en",
  });
  const response = await fetch(`${PHOTON_URL}/api/?${params}`, { signal });
  if (!response.ok) throw new Error("Place search is unavailable right now.");
  return toPlaces(await response.json());
}

/** A readable address for a pin, or null if the geocoder knows nothing there. */
export async function reverseGeocode(pin: LatLng, signal?: AbortSignal): Promise<string | null> {
  const params = new URLSearchParams({
    lat: String(pin.latitude),
    lon: String(pin.longitude),
    lang: "en",
  });
  const response = await fetch(`${PHOTON_URL}/reverse?${params}`, { signal });
  if (!response.ok) return null;
  return toPlaces(await response.json())[0]?.label ?? null;
}

/** "City, Region Postcode" for an order's address, without repeating a region that matches
 * the city (Dar es Salaam is both) or a trailing blank postcode. */
export function formatLocality(address: {
  city: string;
  region: string;
  postal_code: string;
}): string {
  const area = [...new Set([address.city, address.region].filter(Boolean))].join(", ");
  return [area, address.postal_code].filter(Boolean).join(" ");
}
