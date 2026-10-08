"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import type { Role } from "@/lib/auth-context";
import { Avatar } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import { useTheme } from "@/lib/theme";
import { ADMIN_SECTIONS, AdminNavSections, isLinkActive } from "@/components/admin-sidebar";

type NavLink = { label: string; href: string };

const GUEST_LINKS: NavLink[] = [
  { label: "Home", href: "/" },
  { label: "Products", href: "/products" },
];

const CUSTOMER_LINKS: NavLink[] = [
  { label: "Home", href: "/" },
  { label: "Products", href: "/products" },
  { label: "Cart", href: "/cart" },
  { label: "Orders", href: "/orders" },
  { label: "Account", href: "/account" },
];

const VENDOR_LINKS: NavLink[] = [
  { label: "Home", href: "/" },
  { label: "My Products", href: "/vendor/products" },
  { label: "Vendor Orders", href: "/vendor/orders" },
  { label: "Earnings", href: "/vendor/earnings" },
  { label: "Reviews", href: "/vendor/reviews" },
  { label: "Account", href: "/account" },
];

const ADMINISTRATOR_LINKS: NavLink[] = ADMIN_SECTIONS.flatMap((section) => section.links);

const RIDER_LINKS: NavLink[] = [
  { label: "Home", href: "/" },
  { label: "Deliveries", href: "/rider/deliveries" },
  { label: "Account", href: "/account" },
];

function linksForRole(role: Role | null): NavLink[] {
  switch (role) {
    case "CUSTOMER":
      return CUSTOMER_LINKS;
    case "VENDOR":
      return VENDOR_LINKS;
    case "ADMINISTRATOR":
      return ADMINISTRATOR_LINKS;
    case "RIDER":
      return RIDER_LINKS;
    default:
      return GUEST_LINKS;
  }
}

const MODE_HOME: Partial<Record<Role, string>> = {
  CUSTOMER: "/",
  VENDOR: "/vendor/products",
};

/** Customer/Vendor switch for an account that holds both roles (one email, both modes). */
function RoleSwitch({
  roles,
  activeRole,
  onSwitch,
}: {
  roles: Role[];
  activeRole: Role | null;
  onSwitch: (role: Role) => void;
}) {
  return (
    <div role="group" aria-label="Switch mode" className="flex rounded-pill bg-hover p-0.5">
      {roles.map((role) => {
        const active = role === activeRole;
        return (
          <button
            key={role}
            type="button"
            aria-pressed={active}
            onClick={() => onSwitch(role)}
            className={cn(
              "rounded-pill px-3 py-1 text-xs font-medium capitalize transition-colors",
              active ? "bg-navy-900 text-on-primary" : "text-text-muted hover:text-text-primary",
            )}
          >
            {role.toLowerCase()}
          </button>
        );
      })}
    </div>
  );
}

function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  const dark = theme === "dark";
  return (
    <button
      type="button"
      aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
      onClick={toggleTheme}
      className="flex h-9 w-9 items-center justify-center rounded-full text-text-muted hover:bg-hover hover:text-text-primary"
    >
      <svg
        viewBox="0 0 20 20"
        fill="none"
        stroke="currentColor"
        strokeWidth={1.6}
        strokeLinecap="round"
        strokeLinejoin="round"
        className="h-5 w-5"
        aria-hidden
      >
        {dark ? (
          <>
            <circle cx="10" cy="10" r="3.5" />
            <path d="M10 2v1.5M10 16.5V18M2 10h1.5M16.5 10H18M4.3 4.3l1.1 1.1M14.6 14.6l1.1 1.1M4.3 15.7l1.1-1.1M14.6 5.4l1.1-1.1" />
          </>
        ) : (
          <path d="M16.5 12.2A7 7 0 0 1 7.8 3.5a7 7 0 1 0 8.7 8.7z" />
        )}
      </svg>
    </button>
  );
}

export function Nav() {
  const router = useRouter();
  const pathname = usePathname();
  const { user, logout, activeRole, setActiveRole } = useAuth();
  const links = linksForRole(activeRole);
  const [mobileOpen, setMobileOpen] = useState(false);
  const canSwitch = !!user && user.roles.length > 1;
  // Administrators have too many destinations for an inline row: they get the sidebar on large
  // screens (AdminSidebar) and the grouped menu below that.
  const isAdmin = activeRole === "ADMINISTRATOR";

  function handleSwitch(role: Role) {
    if (role === activeRole) return;
    setActiveRole(role);
    setMobileOpen(false);
    router.push(MODE_HOME[role] ?? "/");
  }

  async function handleLogout() {
    setMobileOpen(false);
    await logout();
    router.push("/");
  }

  return (
    <div className="sticky top-0 z-10 bg-canvas px-4 pt-4">
      <nav
        className={cn(
          "mx-auto flex items-center justify-between rounded-pill bg-card px-3 py-2 shadow-nav",
          isAdmin ? "max-w-none" : "max-w-6xl",
        )}
      >
        <Link
          href="/"
          className="flex items-center gap-2 pl-2 pr-4 text-base font-semibold text-brand-text"
        >
          <span aria-hidden className="h-2.5 w-2.5 rounded-sm bg-teal-400" />
          E-Mall
        </Link>

        <div className={cn("hidden items-center gap-1", !isAdmin && "md:flex")}>
          {links.map((link) => {
            const active = isLinkActive(pathname, link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  "rounded-pill px-4 py-1.5 text-sm font-medium transition-colors",
                  active ? "bg-navy-900 text-on-primary" : "text-text-muted hover:bg-hover",
                )}
              >
                {link.label}
              </Link>
            );
          })}
        </div>

        <div className="flex items-center gap-3">
          {user ? (
            <>
              {canSwitch && (
                <div className="hidden sm:block">
                  <RoleSwitch roles={user.roles} activeRole={activeRole} onSwitch={handleSwitch} />
                </div>
              )}
              <Link href="/account" className="hidden items-center gap-2 sm:flex">
                <Avatar name={user.name} size="sm" />
                <span className="flex flex-col leading-tight">
                  <span className="text-sm font-medium text-text-primary">{user.name}</span>
                  <span className="text-xs capitalize text-text-muted">
                    {activeRole?.toLowerCase()}
                  </span>
                </span>
              </Link>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleLogout}
                className="hidden sm:inline-flex"
              >
                Logout
              </Button>
            </>
          ) : (
            <div className="hidden items-center gap-2 sm:flex">
              <Button variant="secondary" size="sm" asChild>
                <Link href="/login">Login</Link>
              </Button>
              <Button variant="primary" size="sm" asChild>
                <Link href="/register">Register</Link>
              </Button>
            </div>
          )}
          <ThemeToggle />
          <button
            type="button"
            aria-label="Toggle menu"
            aria-expanded={mobileOpen}
            onClick={() => setMobileOpen((open) => !open)}
            className={cn(
              "flex h-9 w-9 items-center justify-center rounded-full text-text-muted hover:bg-hover",
              isAdmin ? "lg:hidden" : "md:hidden",
            )}
          >
            <span className="sr-only">Toggle menu</span>
            <svg viewBox="0 0 20 20" fill="currentColor" className="h-5 w-5" aria-hidden>
              {mobileOpen ? (
                <path
                  d="M5 5l10 10M15 5L5 15"
                  stroke="currentColor"
                  strokeWidth={1.6}
                  strokeLinecap="round"
                />
              ) : (
                <path
                  d="M3 5h14M3 10h14M3 15h14"
                  stroke="currentColor"
                  strokeWidth={1.6}
                  strokeLinecap="round"
                />
              )}
            </svg>
          </button>
        </div>
      </nav>

      {mobileOpen && (
        <div
          className={cn(
            "mx-auto mt-2 flex max-w-6xl flex-col gap-1 rounded-card bg-card p-3 shadow-nav",
            isAdmin ? "max-h-[calc(100vh-6rem)] overflow-y-auto lg:hidden" : "md:hidden",
          )}
        >
          {canSwitch && user && (
            <div className="mb-1 flex justify-center sm:hidden">
              <RoleSwitch roles={user.roles} activeRole={activeRole} onSwitch={handleSwitch} />
            </div>
          )}
          {isAdmin && <AdminNavSections onNavigate={() => setMobileOpen(false)} />}
          {!isAdmin &&
            links.map((link) => {
              const active = isLinkActive(pathname, link.href);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setMobileOpen(false)}
                  className={cn(
                    "rounded-control px-4 py-2 text-sm font-medium",
                    active ? "bg-navy-900 text-on-primary" : "text-text-muted hover:bg-hover",
                  )}
                >
                  {link.label}
                </Link>
              );
            })}
          <div className="mt-2 flex items-center gap-2 border-t border-border pt-2">
            {user ? (
              <>
                <Avatar name={user.name} size="sm" />
                <span className="flex flex-1 flex-col leading-tight">
                  <span className="text-sm font-medium text-text-primary">{user.name}</span>
                  <span className="text-xs capitalize text-text-muted">
                    {activeRole?.toLowerCase()}
                  </span>
                </span>
                <Button variant="ghost" size="sm" onClick={handleLogout}>
                  Logout
                </Button>
              </>
            ) : (
              <div className="flex w-full gap-2">
                <Button variant="secondary" size="sm" asChild className="flex-1">
                  <Link href="/login" onClick={() => setMobileOpen(false)}>
                    Login
                  </Link>
                </Button>
                <Button variant="primary" size="sm" asChild className="flex-1">
                  <Link href="/register" onClick={() => setMobileOpen(false)}>
                    Register
                  </Link>
                </Button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
