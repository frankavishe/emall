import { cn } from "@/lib/cn";

function initialsFrom(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0]!.slice(0, 2).toUpperCase();
  return `${parts[0]![0]}${parts[parts.length - 1]![0]}`.toUpperCase();
}

const SIZE_CLASSES = {
  sm: "h-8 w-8 text-xs",
  md: "h-10 w-10 text-sm",
  lg: "h-20 w-20 text-2xl",
} as const;

/** A profile photo when `src` is set, otherwise the person's initials. */
export function Avatar({
  name,
  src,
  size = "md",
}: {
  name: string;
  src?: string | null;
  size?: keyof typeof SIZE_CLASSES;
}) {
  if (src) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={src}
        alt=""
        className={cn("shrink-0 rounded-full object-cover", SIZE_CLASSES[size])}
        aria-hidden
      />
    );
  }
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-full bg-navy-900 font-semibold text-on-primary",
        SIZE_CLASSES[size],
      )}
      aria-hidden
    >
      {initialsFrom(name)}
    </span>
  );
}
