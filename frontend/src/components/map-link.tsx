import { mapsUrl, toLatLng } from "@/lib/geo";
import { cn } from "@/lib/cn";

/** "Open in maps" for a saved pin; renders nothing when there's no pin (e.g. older orders, or a
 * shop that hasn't set its location). */
export function MapLink({
  latitude,
  longitude,
  children = "Open in maps",
  className,
}: {
  latitude: string | number | null | undefined;
  longitude: string | number | null | undefined;
  children?: React.ReactNode;
  className?: string;
}) {
  const pin = toLatLng(latitude, longitude);
  if (!pin) return null;
  return (
    <a
      href={mapsUrl(pin)}
      target="_blank"
      rel="noopener noreferrer"
      className={cn("text-sm font-medium text-navy-700 underline dark:text-teal-300", className)}
    >
      {children}
    </a>
  );
}
