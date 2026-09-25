import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

const SIZE_CLASSES = {
  sm: "max-w-sm",
  md: "max-w-3xl",
  lg: "max-w-5xl",
  xl: "max-w-6xl",
} as const;

type PageShellProps = {
  size?: keyof typeof SIZE_CLASSES;
  title?: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
};

export function PageShell({
  size = "lg",
  title,
  description,
  actions,
  children,
  className,
}: PageShellProps) {
  return (
    <main
      className={cn(
        "mx-auto flex w-full flex-col gap-6 px-4 py-8 sm:px-6",
        SIZE_CLASSES[size],
        className,
      )}
    >
      {(title || description || actions) && (
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex flex-col gap-1">
            {title && <h1 className="text-2xl font-semibold text-text-primary">{title}</h1>}
            {description && <p className="text-sm text-text-muted">{description}</p>}
          </div>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </div>
      )}
      {children}
    </main>
  );
}
