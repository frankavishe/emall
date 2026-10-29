import type { ReactNode } from "react";
import { BrandLogo } from "@/components/brand-logo";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/cn";

type ErrorStateProps = {
  /** Big status numeral, e.g. "404". Omit for errors without a meaningful code. */
  code?: string;
  title: ReactNode;
  description?: ReactNode;
  /** Buttons/links rendered in a row under the copy. */
  actions?: ReactNode;
  /** Extra content under the actions (e.g. an error reference id). */
  children?: ReactNode;
  className?: string;
};

/** Branded full-page error message shared by the 404/403/500 pages and inline "not found" states. */
export function ErrorState({
  code,
  title,
  description,
  actions,
  children,
  className,
}: ErrorStateProps) {
  return (
    <main
      className={cn(
        "mx-auto flex w-full flex-1 flex-col items-center justify-center px-4 py-16 sm:px-6",
        className,
      )}
    >
      {/* Width lives on the card: the admin frame overrides max-width on direct <main> children. */}
      <Card className="flex w-full max-w-lg flex-col items-center gap-4 text-center sm:p-10">
        <BrandLogo className="h-8" />
        {code && (
          <p className="font-mono text-6xl font-bold tracking-tight text-brand-text sm:text-7xl">
            {code}
          </p>
        )}
        <h1 className="text-2xl font-semibold text-text-primary">{title}</h1>
        {description && <p className="max-w-sm text-sm text-text-muted">{description}</p>}
        {actions && (
          <div className="mt-2 flex flex-wrap items-center justify-center gap-2">{actions}</div>
        )}
        {children}
      </Card>
    </main>
  );
}
