"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Avatar } from "@/components/ui/avatar";
import { ThemeToggle } from "@/components/nav";

/** Slim header above admin pages on large screens: theme toggle and the account menu. Below
 * `lg` the regular nav (with the admin menu) takes over. */
export function AdminTopBar() {
  const router = useRouter();
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function handlePointer(event: MouseEvent) {
      if (!menuRef.current?.contains(event.target as Node)) setOpen(false);
    }
    function handleKey(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", handlePointer);
    document.addEventListener("keydown", handleKey);
    return () => {
      document.removeEventListener("mousedown", handlePointer);
      document.removeEventListener("keydown", handleKey);
    };
  }, [open]);

  async function handleLogout() {
    setOpen(false);
    await logout();
    router.push("/");
  }

  if (!user) return null;

  return (
    <header className="sticky top-0 z-10 hidden h-16 items-center justify-end gap-4 border-b border-border bg-card/95 px-8 backdrop-blur lg:flex">
      <ThemeToggle />
      <span aria-hidden className="h-8 w-px bg-border" />
      <div ref={menuRef} className="relative">
        <button
          type="button"
          aria-haspopup="menu"
          aria-expanded={open}
          onClick={() => setOpen((value) => !value)}
          className="flex items-center gap-3 rounded-pill py-1 pl-1 pr-3 transition-colors hover:bg-hover"
        >
          <Avatar name={user.name} />
          <span className="flex flex-col text-left leading-tight">
            <span className="text-sm font-semibold text-text-primary">{user.name}</span>
            <span className="text-xs text-text-muted">Administrator</span>
          </span>
          <svg
            viewBox="0 0 20 20"
            fill="none"
            stroke="currentColor"
            strokeWidth={1.6}
            strokeLinecap="round"
            strokeLinejoin="round"
            className="h-4 w-4 text-text-muted"
            aria-hidden
          >
            <path d="m5 8 5 5 5-5" />
          </svg>
        </button>
        {open && (
          <div
            role="menu"
            className="absolute right-0 mt-2 w-48 rounded-control border border-border bg-card p-1 shadow-card"
          >
            <Link
              href="/account"
              role="menuitem"
              onClick={() => setOpen(false)}
              className="block rounded-control px-3 py-2 text-sm text-text-primary hover:bg-hover"
            >
              Account
            </Link>
            <button
              type="button"
              role="menuitem"
              onClick={handleLogout}
              className="block w-full rounded-control px-3 py-2 text-left text-sm text-text-primary hover:bg-hover"
            >
              Log out
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
