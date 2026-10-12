import { afterEach, describe, expect, it, vi } from "vitest";
import { formatLatLng, mapsUrl, requestCurrentPosition, toLatLng } from "./geo";

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
