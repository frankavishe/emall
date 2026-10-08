import type { ReactNode } from "react";
import { Card } from "./card";
import { cn } from "@/lib/cn";

type StatCardProps = {
  label: string;
  value: ReactNode;
  trend?: { text: string; tone?: "positive" | "neutral" };
  variant?: "default" | "hero";
  icon?: ReactNode;
  /** Caption or link under the figure, e.g. "Process payout →". */
  footer?: ReactNode;
  className?: string;
};

export function StatCard({
  label,
  value,
  trend,
  variant = "default",
  icon,
  footer,
  className,
}: StatCardProps) {
  const hero = variant === "hero";
  return (
    <Card variant={variant} className={cn("flex flex-col gap-3", className)}>
      <div className="flex items-start justify-between gap-2">
        <span
          className={cn("text-sm font-medium", hero ? "text-text-inverse/80" : "text-text-muted")}
        >
          {label}
        </span>
        {icon && (
          <span
            className={cn(
              "flex h-9 w-9 shrink-0 items-center justify-center rounded-control",
              hero ? "text-teal-400" : "bg-card-muted text-text-primary",
            )}
          >
            {icon}
          </span>
        )}
      </div>
      <span className="text-3xl font-bold tracking-tight sm:text-4xl">{value}</span>
      {trend && (
        <span
          className={cn(
            "self-start rounded-pill px-2.5 py-0.5 text-xs font-semibold",
            hero
              ? "bg-white/15 text-text-inverse"
              : trend.tone === "positive"
                ? "bg-teal-100 text-brand-text"
                : "bg-card-muted text-text-muted",
          )}
        >
          {trend.text}
        </span>
      )}
      {footer && (
        <div className={cn("text-xs", hero ? "text-text-inverse/80" : "text-text-muted")}>
          {footer}
        </div>
      )}
    </Card>
  );
}
