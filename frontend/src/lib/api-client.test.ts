import { afterEach, describe, expect, it, beforeEach, vi } from "vitest";
import { ApiError, getAccessToken, refreshAccessToken, setAccessToken } from "./api-client";

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
});
