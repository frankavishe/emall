import { describe, expect, it, beforeEach } from "vitest";
import { ApiError, getAccessToken, setAccessToken } from "./api-client";

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
