import { describe, expect, it } from "vitest";
import { ApiError } from "./api-client";
import { profileFieldErrors, validateProfile } from "./profile";

describe("validateProfile", () => {
  it("accepts a name with an optional phone", () => {
    expect(validateProfile({ name: "Asha Mwita", phone: "" })).toEqual({});
    expect(validateProfile({ name: "Asha Mwita", phone: "+255712345678" })).toEqual({});
    expect(validateProfile({ name: "Asha Mwita", phone: "0712345678" })).toEqual({});
  });

  it("requires a name of at least two characters", () => {
    expect(validateProfile({ name: "   ", phone: "" }).name).toBe("Enter your full name.");
    expect(validateProfile({ name: "A", phone: "" }).name).toMatch(/at least 2/);
  });

  it("rejects a malformed phone", () => {
    expect(validateProfile({ name: "Asha", phone: "12ab" }).phone).toMatch(/valid phone/);
    expect(validateProfile({ name: "Asha", phone: "123" }).phone).toMatch(/valid phone/);
  });
});

describe("profileFieldErrors", () => {
  it("maps DRF field errors onto form fields", () => {
    const err = new ApiError(400, { phone: ["Enter a valid phone number."], other: ["x"] });
    expect(profileFieldErrors(err)).toEqual({ phone: "Enter a valid phone number." });
  });

  it("returns nothing for non-field failures", () => {
    expect(profileFieldErrors(new ApiError(500, { detail: "Boom" }))).toEqual({});
    expect(profileFieldErrors(new Error("offline"))).toEqual({});
  });
});
