import { cn } from "@/lib/cn";

type Option<T extends string> = { value: T; label: string };

type SegmentedToggleProps<T extends string> = {
  options: Option<T>[];
  value: T;
  onChange: (value: T) => void;
  className?: string;
};

export function SegmentedToggle<T extends string>({
  options,
  value,
  onChange,
  className,
}: SegmentedToggleProps<T>) {
  return (
    <div className={cn("inline-flex items-center gap-1 rounded-pill bg-card-muted p-1", className)}>
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          onClick={() => onChange(option.value)}
          className={cn(
            "rounded-pill px-3 py-1.5 text-sm font-medium transition-colors",
            option.value === value ? "bg-navy-900 text-white" : "text-text-muted hover:bg-black/5",
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
