import { cloneElement, isValidElement } from "react";
import type { ButtonHTMLAttributes, ReactElement } from "react";
import { cn } from "@/lib/cn";

type ButtonVariant = "primary" | "secondary" | "danger" | "ghost";
type ButtonSize = "sm" | "md";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
  asChild?: boolean;
  fullWidth?: boolean;
};

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary: "bg-navy-900 text-white hover:bg-navy-800",
  secondary: "bg-card text-text-primary border border-border hover:bg-card-muted",
  danger:
    "bg-card text-status-cancelled border border-status-cancelled/30 hover:bg-status-cancelled/10",
  ghost: "text-text-muted hover:bg-black/5",
};

const SIZE_CLASSES: Record<ButtonSize, string> = {
  sm: "px-3 py-1.5 text-sm",
  md: "px-4 py-2 text-sm",
};

export function Button({
  variant = "primary",
  size = "md",
  asChild,
  fullWidth,
  className,
  children,
  ...props
}: ButtonProps) {
  const classes = cn(
    "inline-flex items-center justify-center gap-2 rounded-pill font-medium transition-colors disabled:opacity-50 disabled:pointer-events-none",
    VARIANT_CLASSES[variant],
    SIZE_CLASSES[size],
    fullWidth && "w-full",
    className,
  );

  if (asChild && isValidElement(children)) {
    const child = children as ReactElement<{ className?: string }>;
    return cloneElement(child, {
      className: cn(classes, child.props.className),
    });
  }

  return (
    <button type="button" className={classes} {...props}>
      {children}
    </button>
  );
}
