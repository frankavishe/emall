import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, renderHook } from "@testing-library/react";
import type { AuthUser } from "@/lib/auth-context";
import { useRequireRole } from "./use-api";

const replace = vi.fn();
let auth: { user: AuthUser | null; isLoading: boolean };

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace }) }));
vi.mock("@/lib/auth-context", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/auth-context")>()),
  useAuth: () => auth,
}));

const CUSTOMER = { id: "1", roles: ["CUSTOMER"] } as unknown as AuthUser;

afterEach(cleanup);
beforeEach(() => {
  replace.mockReset();
});

describe("useRequireRole", () => {
  it("sends signed-out visitors to /login", () => {
    auth = { user: null, isLoading: false };
    const { result } = renderHook(() => useRequireRole("ADMINISTRATOR"));
    expect(result.current).toBe(false);
    expect(replace).toHaveBeenCalledWith("/login");
  });

  it("sends signed-in users without the role to /forbidden", () => {
    auth = { user: CUSTOMER, isLoading: false };
    renderHook(() => useRequireRole("ADMINISTRATOR"));
    expect(replace).toHaveBeenCalledWith("/forbidden");
  });

  it("allows users holding the role", () => {
    auth = { user: CUSTOMER, isLoading: false };
    const { result } = renderHook(() => useRequireRole("CUSTOMER"));
    expect(result.current).toBe(true);
    expect(replace).not.toHaveBeenCalled();
  });

  it("waits while auth is loading", () => {
    auth = { user: null, isLoading: true };
    renderHook(() => useRequireRole("CUSTOMER"));
    expect(replace).not.toHaveBeenCalled();
  });
});
