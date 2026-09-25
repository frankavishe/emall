import type { ReactNode } from "react";
import { Card } from "./card";
import { cn } from "@/lib/cn";

type StatCardProps = {
  label: string;
  value: ReactNode;
  trend?: { text: string; tone?: "positive" | "neutral" };
  variant?: "default" | "hero";
  icon?: ReactNode;
  className?: string;
};

export function StatCard({ label, value, trend, variant = "default", icon, className }: StatCardProps) {
  return (
    <Card variant={variant} className={cn("flex flex-col gap-3", className)}>
      <div className="flex items-center justify-between gap-2">
        <span className={cn("text-sm font-medium", variant === "hero" ? "text-text-inverse/70" : "text-text-muted")}>
          {label}
        </span>
        {icon}
      </div>
      <div className="flex items-center gap-2">
        <span className="text-3xl font-semibold">{value}</span>
        {trend && (
          <span
            className={cn(
              "rounded-pill px-2 py-0.5 text-xs font-medium",
              variant === "hero"
                ? "bg-white/15 text-text-inverse"
                : trend.tone === "positive"
                  ? "bg-teal-100 text-navy-900"
                  : "bg-card-muted text-text-muted",
            )}
          >
            {trend.text}
          </span>
        )}
      </div>
    </Card>
  );
}
