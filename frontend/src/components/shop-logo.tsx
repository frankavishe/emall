import { cn } from "@/lib/cn";

const SIZE_CLASSES = {
  xs: "h-5 w-5 text-[10px]",
  sm: "h-8 w-8 text-xs",
  md: "h-10 w-10 text-sm",
  lg: "h-16 w-16 text-lg",
} as const;

/** A shop's logo, falling back to its initial in a circle when it has none. */
export function ShopLogo({
  url,
  name,
  size = "sm",
  className,
}: {
  url: string | null | undefined;
  name: string;
  size?: keyof typeof SIZE_CLASSES;
  className?: string;
}) {
  const sizeClass = SIZE_CLASSES[size];
  if (url) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={url}
        alt={`${name} logo`}
        className={cn(
          "shrink-0 rounded-full border border-border bg-white object-cover",
          sizeClass,
          className,
        )}
      />
    );
  }
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-full bg-navy-900 font-semibold text-white",
        sizeClass,
        className,
      )}
      aria-hidden
    >
      {name.trim().charAt(0).toUpperCase() || "?"}
    </span>
  );
}
