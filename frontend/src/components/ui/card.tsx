import type { ComponentPropsWithoutRef, ElementType, ReactNode } from "react";
import { cn } from "@/lib/cn";

type CardOwnProps<T extends ElementType> = {
  as?: T;
  variant?: "default" | "hero" | "muted";
  padding?: "sm" | "md" | "none";
  className?: string;
  children: ReactNode;
};

type CardProps<T extends ElementType> = CardOwnProps<T> &
  Omit<ComponentPropsWithoutRef<T>, keyof CardOwnProps<T>>;

const VARIANT_CLASSES = {
  default: "bg-card text-text-primary shadow-card",
  hero: "bg-navy-900 text-text-inverse shadow-card",
  muted: "bg-card-muted text-text-primary",
} as const;

const PADDING_CLASSES = {
  none: "",
  sm: "p-4",
  md: "p-6",
} as const;

export function Card<T extends ElementType = "div">({
  as,
  variant = "default",
  padding = "md",
  className,
  children,
  ...rest
}: CardProps<T>) {
  const Component = (as ?? "div") as ElementType;
  return (
    <Component
      className={cn("rounded-card", VARIANT_CLASSES[variant], PADDING_CLASSES[padding], className)}
      {...rest}
    >
      {children}
    </Component>
  );
}
