"use client";

import type { ReactNode } from "react";
import { useAuth } from "@/lib/auth-context";
import { AdminSidebar } from "@/components/admin-sidebar";
import { AdminTopBar } from "@/components/admin-top-bar";
import { Footer } from "@/components/footer";

/** Page content + footer. Administrators get the full-height sidebar and top bar on large
 * screens instead of the footer, so their content column is pushed right by the rail (w-64).
 * Admin pages share one wide, left-aligned content width whatever PageShell size they ask for. */
export function AppFrame({ children }: { children: ReactNode }) {
  const { activeRole } = useAuth();

  if (activeRole !== "ADMINISTRATOR") {
    return (
      <>
        {children}
        <Footer />
      </>
    );
  }

  return (
    <>
      <AdminSidebar />
      <div className="flex min-w-0 flex-1 flex-col lg:pl-64 lg:[&>main]:mx-0 lg:[&>main]:max-w-6xl lg:[&>main]:px-8">
        <AdminTopBar />
        {children}
      </div>
    </>
  );
}
