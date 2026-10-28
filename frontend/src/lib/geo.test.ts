import { afterEach, describe, expect, it, vi } from "vitest";
import {
  formatLatLng,
  formatLocality,
  mapsUrl,
  requestCurrentPosition,
  searchPlaces,
  toLatLng,
} from "./geo";

function stubGeolocation(getCurrentPosition: Geolocation["getCurrentPosition"] | undefined) {
  vi.stubGlobal("navigator", {
    geolocation: getCurrentPosition ? { getCurrentPosition } : undefined,
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("toLatLng", () => {
  it("parses API decimal strings", () => {
    expect(toLatLng("-6.792400", "39.208300")).toEqual({ latitude: -6.7924, longitude: 39.2083 });
  });

  it("returns null when either coordinate is missing or invalid", () => {
    expect(toLatLng(null, "39.2")).toBeNull();
    expect(toLatLng("-6.7", undefined)).toBeNull();
    expect(toLatLng("", "")).toBeNull();
    expect(toLatLng("abc", "39.2")).toBeNull();
  });
});

describe("mapsUrl / formatLatLng", () => {
  it("builds a maps search link for the exact spot", () => {
    expect(mapsUrl({ latitude: -6.7924, longitude: 39.2083 })).toBe(
      "https://www.google.com/maps/search/?api=1&query=-6.7924,39.2083",
    );
  });

  it("formats to five decimal places", () => {
    expect(formatLatLng({ latitude: -6.792412345, longitude: 39.2 })).toBe("-6.79241, 39.20000");
  });
});

describe("requestCurrentPosition", () => {
  it("resolves with the device's coordinates", async () => {
    stubGeolocation((success) =>
      success({ coords: { latitude: -6.8, longitude: 39.28 } } as GeolocationPosition),
    );

    await expect(requestCurrentPosition()).resolves.toEqual({ latitude: -6.8, longitude: 39.28 });
  });

  it("explains a denied permission", async () => {
    stubGeolocation((_success, failure) =>
      failure?.({ code: 1, message: "denied" } as GeolocationPositionError),
    );

    await expect(requestCurrentPosition()).rejects.toThrow(/permission was denied/);
  });

  it("explains a timeout", async () => {
    stubGeolocation((_success, failure) =>
      failure?.({ code: 3, message: "timeout" } as GeolocationPositionError),
    );

    await expect(requestCurrentPosition()).rejects.toThrow(/took too long/);
  });

  it("falls back to the pin when the browser has no geolocation", async () => {
    stubGeolocation(undefined);

    await expect(requestCurrentPosition()).rejects.toThrow(/drop the pin/i);
  });
});

describe("searchPlaces", () => {
  it("queries within Dar es Salaam and maps results to labelled pins", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        features: [
          {
            geometry: { coordinates: [39.2735, -6.8162] },
            properties: { name: "Kariakoo Market", district: "Kariakoo", city: "Dar es Salaam" },
          },
          { geometry: { coordinates: [39.2, -6.8] }, properties: {} },
        ],
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const places = await searchPlaces("Kariakoo");

    expect(fetchMock.mock.calls[0][0]).toContain("bbox=38.95%2C-7.25%2C39.65%2C-6.55");
    expect(places).toEqual([
      {
        label: "Kariakoo Market, Kariakoo, Dar es Salaam",
        pin: { latitude: -6.8162, longitude: 39.2735 },
      },
    ]);
  });

  it("throws when the geocoder is down", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false }));
    await expect(searchPlaces("Kariakoo")).rejects.toThrow();
  });
});

describe("formatLocality", () => {
  it("doesn't repeat a region equal to the city or show a blank postcode", () => {
    expect(
      formatLocality({ city: "Dar es Salaam", region: "Dar es Salaam", postal_code: "" }),
    ).toBe("Dar es Salaam");
    expect(formatLocality({ city: "Accra", region: "Greater Accra", postal_code: "GA-1" })).toBe(
      "Accra, Greater Accra GA-1",
    );
  });
});
