"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

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
  { label: "Account", href: "/account" },
];

const ADMINISTRATOR_LINKS: NavLink[] = [
  { label: "Home", href: "/" },
  { label: "Shop Approvals", href: "/admin/shops" },
  { label: "Order Oversight", href: "/admin/orders" },
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

export function Nav() {
  const router = useRouter();
  const { user, logout } = useAuth();
  const links = linksForRole(user?.role ?? null);

  async function handleLogout() {
    await logout();
    router.push("/");
  }

  return (
    <nav className="flex items-center justify-between border-b border-black/10 px-6 py-3">
      <div className="flex items-center gap-5">
        {links.map((link) => (
          <Link key={link.href} href={link.href} className="text-sm font-medium">
            {link.label}
          </Link>
        ))}
      </div>
      <div className="flex items-center gap-3">
        {user ? (
          <button
            type="button"
            onClick={handleLogout}
            className="text-sm font-medium text-black/60"
          >
            Logout
          </button>
        ) : (
          <>
            <Link href="/login" className="text-sm font-medium">
              Login
            </Link>
            <Link href="/register" className="text-sm font-medium">
              Register
            </Link>
          </>
        )}
      </div>
    </nav>
  );
}
