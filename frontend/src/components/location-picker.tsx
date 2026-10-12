"use client";

import { useEffect, useRef, useState } from "react";
import type { Map as LeafletMap, Marker } from "leaflet";
import "leaflet/dist/leaflet.css";
import type { LatLng } from "@/lib/api-client";
import { DEFAULT_CENTER, formatLatLng, requestCurrentPosition } from "@/lib/geo";
import { Button } from "@/components/ui/button";
import { ErrorText } from "@/components/ui/status-text";

const PIN_HTML =
  '<svg width="30" height="40" viewBox="0 0 30 40" aria-hidden="true"><path d="M15 0C6.7 0 0 6.6 0 14.8 0 25.9 15 40 15 40s15-14.1 15-25.2C30 6.6 23.3 0 15 0z" fill="#0f2a4a"/><circle cx="15" cy="14.5" r="5.5" fill="#2dd4bf"/></svg>';

/** A map where the user sets one location: tap or click to drop the pin, drag it to adjust, or
 * use the device's GPS. Leaflet is loaded only in the browser, inside an effect, so the page
 * still renders on the server. Map tiles are OpenStreetMap's (free, no API key). */
export function LocationPicker({
  value,
  onChange,
  label = "Delivery location",
}: {
  value: LatLng | null;
  onChange: (pin: LatLng) => void;
  label?: string;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<LeafletMap | null>(null);
  const markerRef = useRef<Marker | null>(null);
  const placeMarkerRef = useRef<((pin: LatLng) => void) | null>(null);
  const onChangeRef = useRef(onChange);
  const valueRef = useRef(value);
  const [isLocating, setIsLocating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tilesFailed, setTilesFailed] = useState(false);

  useEffect(() => {
    onChangeRef.current = onChange;
  }, [onChange]);

  useEffect(() => {
    valueRef.current = value;
  }, [value]);

  useEffect(() => {
    let cancelled = false;

    void import("leaflet").then((L) => {
      if (cancelled || !containerRef.current || mapRef.current) return;
      // The latest pin, which may have arrived (e.g. from GPS) while Leaflet was loading.
      const initial = valueRef.current;
      const start = initial ?? DEFAULT_CENTER;
      const map = L.map(containerRef.current, {
        center: [start.latitude, start.longitude],
        zoom: initial ? 16 : 12,
      });
      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      })
        .on("tileerror", () => setTilesFailed(true))
        .addTo(map);

      const icon = L.divIcon({
        html: PIN_HTML,
        className: "",
        iconSize: [30, 40],
        iconAnchor: [15, 40],
      });

      function placeMarker(pin: LatLng) {
        const position: [number, number] = [pin.latitude, pin.longitude];
        if (markerRef.current) {
          markerRef.current.setLatLng(position);
          return;
        }
        const marker = L.marker(position, { icon, draggable: true, autoPan: true }).addTo(map);
        marker.on("dragend", () => {
          const { lat, lng } = marker.getLatLng();
          onChangeRef.current({ latitude: lat, longitude: lng });
        });
        markerRef.current = marker;
      }
      placeMarkerRef.current = placeMarker;

      if (initial) placeMarker(initial);
      map.on("click", (event) => {
        const pin = { latitude: event.latlng.lat, longitude: event.latlng.lng };
        placeMarker(pin);
        onChangeRef.current(pin);
      });
      mapRef.current = map;
    });

    return () => {
      cancelled = true;
      mapRef.current?.remove();
      mapRef.current = null;
      markerRef.current = null;
      placeMarkerRef.current = null;
    };
  }, []);

  // Follow pins set from outside the map (GPS, or a saved location loaded later).
  useEffect(() => {
    if (!value || !mapRef.current || !placeMarkerRef.current) return;
    const current = markerRef.current?.getLatLng();
    if (current && current.lat === value.latitude && current.lng === value.longitude) return;
    placeMarkerRef.current(value);
    mapRef.current.setView(
      [value.latitude, value.longitude],
      Math.max(mapRef.current.getZoom(), 16),
    );
  }, [value]);

  async function useMyLocation() {
    setError(null);
    setIsLocating(true);
    try {
      onChange(await requestCurrentPosition());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't get your location.");
    } finally {
      setIsLocating(false);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm font-medium text-text-primary">{label}</span>
        <Button variant="secondary" size="sm" onClick={useMyLocation} disabled={isLocating}>
          {isLocating ? "Finding you…" : "Use my location"}
        </Button>
      </div>
      <div
        ref={containerRef}
        className="relative z-0 h-72 w-full overflow-hidden rounded-control border border-border"
        aria-label={`${label} map. Click or tap to drop a pin, then drag it to adjust.`}
        role="application"
      />
      <p className="text-xs text-text-muted">
        {value
          ? `Pin set at ${formatLatLng(value)}. Drag it to adjust.`
          : "Tap the map to drop a pin, or use your location."}
      </p>
      {tilesFailed && (
        <ErrorText>
          The map couldn&apos;t load fully. Check your connection and try again.
        </ErrorText>
      )}
      {error && <ErrorText>{error}</ErrorText>}
    </div>
  );
}
