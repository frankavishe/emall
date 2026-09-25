"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Avatar } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";

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
  { label: "Reviews", href: "/vendor/reviews" },
  { label: "Account", href: "/account" },
];

const ADMINISTRATOR_LINKS: NavLink[] = [
  { label: "Home", href: "/" },
  { label: "Shop Approvals", href: "/admin/shops" },
  { label: "Order Oversight", href: "/admin/orders" },
  { label: "Review Moderation", href: "/admin/reviews" },
  { label: "Account", href: "/account" },
];

function linksForRole(role: "CUSTOMER" | "VENDOR" | "ADMINISTRATOR" | null): NavLink[] {
  switch (role) {
    case "CUSTOMER":
      return CUSTOMER_LINKS;
    case "VENDOR":
      return VENDOR_LINKS;
    case "ADMINISTRATOR":
      return ADMINISTRATOR_LINKS;
    default:
      return GUEST_LINKS;
  }
}

function isLinkActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function Nav() {
  const router = useRouter();
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const links = linksForRole(user?.role ?? null);
  const [mobileOpen, setMobileOpen] = useState(false);

  async function handleLogout() {
    setMobileOpen(false);
    await logout();
    router.push("/");
  }

  return (
    <div className="sticky top-0 z-10 bg-canvas px-4 pt-4">
      <nav className="mx-auto flex max-w-6xl items-center justify-between rounded-pill bg-card px-3 py-2 shadow-nav">
        <Link
          href="/"
          className="flex items-center gap-2 pl-2 pr-4 text-base font-semibold text-navy-900"
        >
          <span aria-hidden className="h-2.5 w-2.5 rounded-sm bg-teal-400" />
          E-Mall
        </Link>

        <div className="hidden items-center gap-1 md:flex">
          {links.map((link) => {
            const active = isLinkActive(pathname, link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  "rounded-pill px-4 py-1.5 text-sm font-medium transition-colors",
                  active ? "bg-navy-900 text-white" : "text-text-muted hover:bg-black/5",
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
              <Link href="/account" className="hidden items-center gap-2 sm:flex">
                <Avatar name={user.name} size="sm" />
                <span className="flex flex-col leading-tight">
                  <span className="text-sm font-medium text-text-primary">{user.name}</span>
                  <span className="text-xs capitalize text-text-muted">
                    {user.role.toLowerCase()}
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
          <button
            type="button"
            aria-label="Toggle menu"
            aria-expanded={mobileOpen}
            onClick={() => setMobileOpen((open) => !open)}
            className="flex h-9 w-9 items-center justify-center rounded-full text-text-muted hover:bg-black/5 md:hidden"
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
        <div className="mx-auto mt-2 flex max-w-6xl flex-col gap-1 rounded-card bg-card p-3 shadow-nav md:hidden">
          {links.map((link) => {
            const active = isLinkActive(pathname, link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMobileOpen(false)}
                className={cn(
                  "rounded-control px-4 py-2 text-sm font-medium",
                  active ? "bg-navy-900 text-white" : "text-text-muted hover:bg-black/5",
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
                    {user.role.toLowerCase()}
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
