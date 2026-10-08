"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { cn } from "@/lib/cn";
import { useAuth } from "@/lib/auth-context";
import { listAdminShops } from "@/lib/api-client";
import { useApi } from "@/lib/use-api";

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

/** Pending shop applications, shown as a badge on the Shop Approvals link. */
function usePendingShopCount(): number | null {
  const { activeRole } = useAuth();
  const pending = useApi(
    () => listAdminShops("PENDING", 1),
    "admin-pending-shops",
    activeRole === "ADMINISTRATOR",
  );
  return pending.data?.count ?? null;
}

const SECTION_VARIANTS = {
  light: {
    title: "text-text-muted",
    link: "rounded-control px-3 py-1.5",
    active: "bg-navy-900 text-on-primary",
    idle: "text-text-muted hover:bg-hover hover:text-text-primary",
  },
  dark: {
    title: "text-white/40",
    link: "relative rounded-control px-3 py-2",
    active:
      "bg-sidebar-active text-white before:absolute before:inset-y-2 before:-left-3 before:w-1 before:rounded-r before:bg-teal-400",
    idle: "text-white/70 hover:bg-white/5 hover:text-white",
  },
} as const;

/** Grouped admin links with icons; shared by the desktop sidebar (dark) and the mobile menu (light). */
export function AdminNavSections({
  onNavigate,
  variant = "light",
}: {
  onNavigate?: () => void;
  variant?: keyof typeof SECTION_VARIANTS;
}) {
  const pathname = usePathname();
  const pendingShops = usePendingShopCount();
  const styles = SECTION_VARIANTS[variant];
  return (
    <div className={cn("flex flex-col", variant === "dark" ? "gap-6" : "gap-4")}>
      {ADMIN_SECTIONS.map((section) => (
        <div key={section.title} className="flex flex-col gap-0.5">
          <p
            className={cn(
              "mb-1 px-3 text-[11px] font-semibold uppercase tracking-wider",
              styles.title,
            )}
          >
            {section.title}
          </p>
          {section.links.map((link) => {
            const active = isLinkActive(pathname, link.href);
            const badge = link.href === "/admin/shops" && pendingShops ? pendingShops : null;
            return (
              <Link
                key={link.href}
                href={link.href}
                onClick={onNavigate}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex items-center gap-3 text-sm font-medium transition-colors",
                  styles.link,
                  active ? styles.active : styles.idle,
                )}
              >
                {link.icon}
                <span className="flex-1">{link.label}</span>
                {badge !== null && (
                  <span
                    className="rounded-pill bg-teal-400 px-2 py-0.5 text-[11px] font-semibold text-navy-900"
                    aria-label={`${badge} pending`}
                  >
                    {badge}
                  </span>
                )}
              </Link>
            );
          })}
        </div>
      ))}
    </div>
  );
}

/** Full-height dark rail for administrators on large screens. Below `lg` the same sections live
 * in the nav's menu, and `AppFrame` only reserves space for the rail at `lg` and up. */
export function AdminSidebar() {
  const router = useRouter();
  const { logout } = useAuth();

  async function handleLogout() {
    await logout();
    router.push("/");
  }

  return (
    <aside
      aria-label="Admin navigation"
      className="fixed inset-y-0 left-0 z-20 hidden w-64 flex-col bg-sidebar text-white lg:flex"
    >
      <Link href="/" className="flex items-center gap-3 px-6 py-5">
        <span
          aria-hidden
          className="flex h-9 w-9 items-center justify-center rounded-full bg-teal-400 text-sm font-bold text-navy-900"
        >
          E
        </span>
        <span className="text-lg font-semibold">E-Mall</span>
        <span className="ml-auto rounded-pill bg-white/10 px-2 py-0.5 text-[10px] font-semibold tracking-wider text-white/70">
          ADMIN
        </span>
      </Link>
      <div className="flex-1 overflow-y-auto px-3 py-2 [scrollbar-width:none]">
        <AdminNavSections variant="dark" />
      </div>
      <div className="border-t border-white/10 p-3">
        <button
          type="button"
          onClick={handleLogout}
          className="flex w-full items-center gap-3 rounded-control px-3 py-2 text-sm font-medium text-white/70 transition-colors hover:bg-white/5 hover:text-white"
        >
          <Icon>
            <path d="M8 3.5H4.5a1 1 0 0 0-1 1v11a1 1 0 0 0 1 1H8M12 6.5 15.5 10 12 13.5M15.5 10H7.5" />
          </Icon>
          Log out
        </button>
      </div>
    </aside>
  );
}
