"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, errorMessage } from "@/lib/api-client";
import { hasRole, useAuth, type Role } from "@/lib/auth-context";

/** Sends signed-out visitors to /login and signed-in users without `role` to /forbidden
 * (convenience only — the API enforces roles). Returns true once the signed-in user is known
 * to hold `role`. */
export function useRequireRole(role: Role): boolean {
  const router = useRouter();
  const { user, isLoading } = useAuth();
  const allowed = !isLoading && !!user && hasRole(user, role);

  useEffect(() => {
    if (!isLoading && (!user || !hasRole(user, role))) {
      router.replace(user ? "/forbidden" : "/login");
    }
  }, [isLoading, user, role, router]);

  return allowed;
}

/** Runs `load` whenever `enabled` is true and `key` changes; ignores stale responses. */
export function useApi<T>(load: () => Promise<T>, key: string, enabled: boolean) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  /** HTTP status of the last failure, when the API answered (null for network errors). */
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;

    async function run() {
      setIsLoading(true);
      setError(null);
      setErrorStatus(null);
      try {
        const result = await load();
        if (!cancelled) setData(result);
      } catch (err) {
        if (!cancelled) {
          setError(errorMessage(err));
          setErrorStatus(err instanceof ApiError ? err.status : null);
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    void run();
    return () => {
      cancelled = true;
    };
    // `load` is keyed by `key` rather than its identity (callers pass inline lambdas).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, key, version]);

  const reload = useCallback(() => setVersion((v) => v + 1), []);
  return { data, error, errorStatus, isLoading, reload };
}
