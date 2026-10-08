"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/cn";

type AdminLink = { label: string; href: string; icon: ReactNode };
export type AdminSection = { title: string; links: AdminLink[] };

function Icon({ children }: { children: ReactNode }) {
  return (
    <svg
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.6}
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-[18px] w-[18px] shrink-0"
      aria-hidden
    >
      {children}
    </svg>
  );
}

/** Administrator navigation, grouped. Drives the desktop sidebar and the mobile menu. */
export const ADMIN_SECTIONS: AdminSection[] = [
  {
    title: "Overview",
    links: [
      {
        label: "Home",
        href: "/",
        icon: (
          <Icon>
            <path d="M3 9.5 10 4l7 5.5V16a1 1 0 0 1-1 1h-3.5v-4.5h-5V17H4a1 1 0 0 1-1-1z" />
          </Icon>
        ),
      },
      {
        label: "Finance",
        href: "/admin/finance",
        icon: (
          <Icon>
            <path d="M3 16.5h14M5 13.5V9M8.5 13.5V6M12 13.5v-3M15.5 13.5V4" />
          </Icon>
        ),
      },
      {
        label: "Transactions",
        href: "/admin/transactions",
        icon: (
          <Icon>
            <path d="M4 7h11l-3-3M16 13H5l3 3" />
          </Icon>
        ),
      },
    ],
  },
  {
    title: "Marketplace",
    links: [
      {
        label: "Shop Approvals",
        href: "/admin/shops",
        icon: (
          <Icon>
            <path d="M3.5 8 5 3.5h10L16.5 8M3.5 8v8.5h13V8M3.5 8h13M8 16.5V12h4v4.5" />
          </Icon>
        ),
      },
      {
        label: "Products",
        href: "/admin/products",
        icon: (
          <Icon>
            <path d="m10 2.5 6.5 3.5v8L10 17.5 3.5 14V6zM3.5 6 10 9.5 16.5 6M10 9.5v8" />
          </Icon>
        ),
      },
      {
        label: "Categories",
        href: "/admin/categories",
        icon: (
          <Icon>
            <path d="M3.5 3.5h5v5h-5zM11.5 3.5h5v5h-5zM3.5 11.5h5v5h-5zM11.5 11.5h5v5h-5z" />
          </Icon>
        ),
      },
    ],
  },
  {
    title: "People",
    links: [
      {
        label: "Customers",
        href: "/admin/customers",
        icon: (
          <Icon>
            <circle cx="8" cy="7" r="3" />
            <path d="M2.5 16.5a5.5 5.5 0 0 1 11 0M13.5 4.2a3 3 0 0 1 0 5.6M15.5 12a5.5 5.5 0 0 1 2 4.5" />
          </Icon>
        ),
      },
      {
        label: "Riders",
        href: "/admin/riders",
        icon: (
          <Icon>
            <circle cx="5" cy="14" r="2.5" />
            <circle cx="15" cy="14" r="2.5" />
            <path d="M5 14 8 8h4l3 6M8 8 7 5H5M12 8l1-3h2" />
          </Icon>
        ),
      },
    ],
  },
  {
    title: "Operations",
    links: [
      {
        label: "Order Oversight",
        href: "/admin/orders",
        icon: (
          <Icon>
            <path d="M6 3.5h8a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1v-12a1 1 0 0 1 1-1zM8 7.5h4M8 10.5h4M8 13.5h2" />
          </Icon>
        ),
      },
      {
        label: "Review Moderation",
        href: "/admin/reviews",
        icon: (
          <Icon>
            <path d="m10 3 2.1 4.3 4.7.7-3.4 3.3.8 4.7L10 13.8 5.8 16l.8-4.7L3.2 8l4.7-.7z" />
          </Icon>
        ),
      },
    ],
  },
  {
    title: "You",
    links: [
      {
        label: "Account",
        href: "/account",
        icon: (
          <Icon>
            <circle cx="10" cy="7" r="3.5" />
            <path d="M3.5 17a6.5 6.5 0 0 1 13 0" />
          </Icon>
        ),
      },
    ],
  },
];

export function isLinkActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

/** Grouped admin links with icons; shared by the desktop sidebar and the mobile menu. */
export function AdminNavSections({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <div className="flex flex-col gap-4">
      {ADMIN_SECTIONS.map((section) => (
        <div key={section.title} className="flex flex-col gap-0.5">
          <p className="px-3 text-[11px] font-semibold uppercase tracking-wider text-text-muted">
            {section.title}
          </p>
          {section.links.map((link) => {
            const active = isLinkActive(pathname, link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                onClick={onNavigate}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex items-center gap-3 rounded-control px-3 py-1.5 text-sm font-medium transition-colors",
                  active
                    ? "bg-navy-900 text-on-primary"
                    : "text-text-muted hover:bg-hover hover:text-text-primary",
                )}
              >
                {link.icon}
                {link.label}
              </Link>
            );
          })}
        </div>
      ))}
    </div>
  );
}

/** Fixed left rail for administrators on large screens. Below `lg` the same sections live in
 * the nav's menu, and `AppFrame` only reserves space for the rail at `lg` and up. */
export function AdminSidebar() {
  return (
    <aside
      aria-label="Admin navigation"
      className="fixed bottom-4 left-4 top-[5.5rem] z-10 hidden w-60 overflow-y-auto rounded-card bg-card p-3 shadow-nav lg:block"
    >
      <AdminNavSections />
    </aside>
  );
}
