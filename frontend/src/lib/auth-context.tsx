"use client";

/**
 * React context holding the access token and current user profile in memory only (task T019).
 * Never persisted to localStorage — Constitution Principle III, research.md §7.
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { apiFetch, refreshAccessToken, setAccessToken } from "./api-client";

export type Shop = {
  id: string;
  name: string;
  status: "PENDING" | "APPROVED" | "REJECTED";
  status_reason?: string | null;
};

export type AuthUser = {
  id: string;
  name: string;
  email: string;
  role: "CUSTOMER" | "VENDOR" | "ADMINISTRATOR";
  is_email_verified: boolean;
  shops?: Shop[];
};

type LoginResponse = { access: string; user: AuthUser };

type AuthContextValue = {
  user: AuthUser | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  registerCustomer: (name: string, email: string, password: string) => Promise<void>;
  registerVendor: (
    name: string,
    email: string,
    password: string,
    shopName: string,
  ) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  requestShop: (name: string) => Promise<void>;
  resendVerificationEmail: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    const me = await apiFetch<AuthUser>("/api/auth/me");
    setUser(me);
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function restoreSession() {
      const token = await refreshAccessToken();
      if (cancelled) return;
      if (!token) {
        setUser(null);
        setIsLoading(false);
        return;
      }
      try {
        await refreshUser();
      } catch {
        setUser(null);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    void restoreSession();
    return () => {
      cancelled = true;
    };
  }, [refreshUser]);

  const login = useCallback(
    async (email: string, password: string) => {
      // Fetches the full profile via refreshUser() (/api/auth/me) rather than trusting the
      // login response's `user` field directly — that field omits `shops` for a Vendor, which
      // previously left a Vendor who logged in (as opposed to just registering) with no shops
      // showing until an unrelated page reload happened to trigger restoreSession()/refreshUser().
      const result = await apiFetch<LoginResponse>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      setAccessToken(result.access);
      await refreshUser();
    },
    [refreshUser],
  );

  const registerCustomer = useCallback(async (name: string, email: string, password: string) => {
    const result = await apiFetch<LoginResponse>("/api/auth/register/customer", {
      method: "POST",
      body: JSON.stringify({ name, email, password }),
    });
    setAccessToken(result.access);
    setUser(result.user);
  }, []);

  const registerVendor = useCallback(
    async (name: string, email: string, password: string, shopName: string) => {
      const result = await apiFetch<LoginResponse & { shops: Shop[] }>(
        "/api/auth/register/vendor",
        {
          method: "POST",
          body: JSON.stringify({ name, email, password, shop_name: shopName }),
        },
      );
      setAccessToken(result.access);
      setUser({ ...result.user, shops: result.shops });
    },
    [],
  );

  const requestShop = useCallback(
    async (name: string) => {
      await apiFetch<Shop>("/api/vendor/shops", {
        method: "POST",
        body: JSON.stringify({ name }),
      });
      await refreshUser();
    },
    [refreshUser],
  );

  const resendVerificationEmail = useCallback(async () => {
    await apiFetch("/api/auth/verify-email/request", { method: "POST" });
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiFetch("/api/auth/logout", { method: "POST" });
    } finally {
      setAccessToken(null);
      setUser(null);
    }
  }, []);

  const value = useMemo(
    () => ({
      user,
      isLoading,
      login,
      registerCustomer,
      registerVendor,
      logout,
      refreshUser,
      requestShop,
      resendVerificationEmail,
    }),
    [
      user,
      isLoading,
      login,
      registerCustomer,
      registerVendor,
      logout,
      refreshUser,
      requestShop,
      resendVerificationEmail,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
