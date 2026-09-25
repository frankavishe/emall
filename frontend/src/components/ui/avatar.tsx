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
} as const;

export function Avatar({ name, size = "md" }: { name: string; size?: keyof typeof SIZE_CLASSES }) {
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-full bg-navy-900 font-semibold text-white",
        SIZE_CLASSES[size],
      )}
      aria-hidden
    >
      {initialsFrom(name)}
    </span>
  );
}
