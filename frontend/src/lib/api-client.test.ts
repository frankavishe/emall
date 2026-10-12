import { afterEach, describe, expect, it, beforeEach, vi } from "vitest";
import {
  ApiError,
  apiFetch,
  getAccessToken,
  refreshAccessToken,
  setAccessToken,
} from "./api-client";

describe("ApiError", () => {
  it("extracts the detail message from a DRF-style error body", () => {
    const error = new ApiError(400, { detail: "Invalid credentials" });
    expect(error.message).toBe("Invalid credentials");
    expect(error.status).toBe(400);
    expect(error.body).toEqual({ detail: "Invalid credentials" });
  });

  it("falls back to a generic message when the body has no detail field", () => {
    const error = new ApiError(500, { unrelated: true });
    expect(error.message).toBe("Request failed with status 500");
  });

  it("falls back to a generic message when the body is not an object", () => {
    const error = new ApiError(404, null);
    expect(error.message).toBe("Request failed with status 404");
  });
});

describe("access token store", () => {
  beforeEach(() => {
    setAccessToken(null);
  });

  it("returns null before any token is set", () => {
    expect(getAccessToken()).toBeNull();
  });

  it("stores and returns the token that was set", () => {
    setAccessToken("test-token");
    expect(getAccessToken()).toBe("test-token");
  });
});

describe("refreshAccessToken", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    fetchMock.mockReset();
    vi.unstubAllGlobals();
    setAccessToken(null);
  });

  it("returns null instead of throwing when the API is unreachable", async () => {
    setAccessToken("existing");
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));

    await expect(refreshAccessToken()).resolves.toBeNull();
    // A transient outage must not wipe the current session's token.
    expect(getAccessToken()).toBe("existing");
  });

  it("stores and returns the new access token on success", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ access: "fresh" }), { status: 200 }));

    await expect(refreshAccessToken()).resolves.toBe("fresh");
    expect(getAccessToken()).toBe("fresh");
  });

  it("clears the access token when the refresh is rejected", async () => {
    setAccessToken("stale");
    fetchMock.mockResolvedValue(new Response(null, { status: 401 }));

    await expect(refreshAccessToken()).resolves.toBeNull();
    expect(getAccessToken()).toBeNull();
  });

  it("does not clear a token set while a failing refresh was in flight", async () => {
    setAccessToken("stale");
    let settle!: (response: Response) => void;
    fetchMock.mockReturnValue(new Promise<Response>((resolve) => (settle = resolve)));

    const pending = refreshAccessToken();
    setAccessToken("from-login");
    settle(new Response(null, { status: 401 }));

    await expect(pending).resolves.toBeNull();
    expect(getAccessToken()).toBe("from-login");
  });
});

describe("concurrent 401s", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    fetchMock.mockReset();
    vi.unstubAllGlobals();
    setAccessToken(null);
  });

  it("share a single refresh and both retry with the new token", async () => {
    setAccessToken("expired");
    fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
      if (url.endsWith("/api/auth/refresh")) {
        // A second refresh with the now-rotated cookie would be rejected by the backend.
        const refreshes = fetchMock.mock.calls.filter(([u]) => String(u).endsWith("/refresh"));
        return refreshes.length === 1
          ? new Response(JSON.stringify({ access: "fresh" }), { status: 200 })
          : new Response(null, { status: 401 });
      }
      const auth = new Headers(init?.headers).get("Authorization");
      return auth === "Bearer fresh"
        ? new Response(JSON.stringify({ ok: url }), { status: 200 })
        : new Response(null, { status: 401 });
    });

    const [a, b] = await Promise.all([apiFetch("/api/a"), apiFetch("/api/b")]);

    expect(a).toEqual({ ok: expect.stringContaining("/api/a") });
    expect(b).toEqual({ ok: expect.stringContaining("/api/b") });
    expect(getAccessToken()).toBe("fresh");
    const refreshCalls = fetchMock.mock.calls.filter(([u]) => String(u).endsWith("/refresh"));
    expect(refreshCalls).toHaveLength(1);
  });
});
