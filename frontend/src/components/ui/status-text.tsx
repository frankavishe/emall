import type { ReactNode } from "react";

export function LoadingText({ children = "Loading…" }: { children?: ReactNode }) {
  return <p className="text-sm text-text-muted">{children}</p>;
}

export function ErrorText({ children }: { children: ReactNode }) {
  return <p className="text-sm text-status-cancelled">{children}</p>;
}

export function EmptyText({ children }: { children: ReactNode }) {
  return <p className="text-sm text-text-muted">{children}</p>;
}
