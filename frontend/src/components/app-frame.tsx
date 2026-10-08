"use client";

import type { ReactNode } from "react";
import { useAuth } from "@/lib/auth-context";
import { AdminSidebar } from "@/components/admin-sidebar";

/** Page content + footer. Administrators get the fixed sidebar on large screens, so the content
 * column is pushed right by the rail's width (w-60) plus its gutters. */
export function AppFrame({ children }: { children: ReactNode }) {
  const { activeRole } = useAuth();

  if (activeRole !== "ADMINISTRATOR") return <>{children}</>;

  return (
    <>
      <AdminSidebar />
      <div className="flex min-w-0 flex-1 flex-col lg:pl-[17rem]">{children}</div>
    </>
  );
}
