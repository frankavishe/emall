import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { PersonalInfoForm } from "./personal-info-form";
import { ApiError } from "@/lib/api-client";
import type { AuthUser } from "@/lib/auth-context";

const refreshUser = vi.fn();
const updateMyProfile = vi.fn();

vi.mock("@/lib/auth-context", () => ({ useAuth: () => ({ refreshUser }) }));
vi.mock("@/lib/api-client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api-client")>()),
  updateMyProfile: (...args: unknown[]) => updateMyProfile(...args),
}));

const USER: AuthUser = {
  id: "1",
  name: "Asha Mwita",
  email: "asha@example.com",
  phone: "",
  avatar_url: null,
  role: "ADMINISTRATOR",
  roles: ["ADMINISTRATOR"],
  is_email_verified: true,
  admin_role: "SUPPORT_ADMIN",
  admin_role_label: "Support Admin",
  permissions: [],
  date_joined: "2026-01-01T00:00:00Z",
  last_login: null,
};

beforeEach(() => {
  refreshUser.mockResolvedValue(undefined);
  updateMyProfile.mockResolvedValue(undefined);
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

function openEditor() {
  render(<PersonalInfoForm user={USER} />);
  fireEvent.click(screen.getByRole("button", { name: "Edit profile" }));
}

const nameInput = () => screen.getByLabelText("Full name") as HTMLInputElement;
const phoneInput = () => screen.getByLabelText("Phone") as HTMLInputElement;
const save = () => fireEvent.click(screen.getByRole("button", { name: "Save changes" }));

describe("PersonalInfoForm", () => {
  it("shows the details read-only with email not editable", () => {
    render(<PersonalInfoForm user={USER} />);
    expect(screen.getByText("asha@example.com")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Edit profile" }));
    expect((screen.getByLabelText(/^Email/) as HTMLInputElement).disabled).toBe(true);
  });

  it("blocks an invalid form without calling the API", () => {
    openEditor();
    fireEvent.change(nameInput(), { target: { value: "" } });
    fireEvent.change(phoneInput(), { target: { value: "12ab" } });
    save();

    expect(screen.getByText("Enter your full name.")).toBeTruthy();
    expect(screen.getByText(/valid phone number/)).toBeTruthy();
    expect(updateMyProfile).not.toHaveBeenCalled();
  });

  it("saves trimmed values and refreshes the profile", async () => {
    openEditor();
    fireEvent.change(nameInput(), { target: { value: "  Asha M. Mwita " } });
    fireEvent.change(phoneInput(), { target: { value: "+255712345678" } });
    save();

    await waitFor(() => expect(screen.getByText("Profile saved.")).toBeTruthy());
    expect(updateMyProfile).toHaveBeenCalledWith({ name: "Asha M. Mwita", phone: "+255712345678" });
    expect(refreshUser).toHaveBeenCalled();
  });

  it("shows server field errors next to the field", async () => {
    updateMyProfile.mockRejectedValue(new ApiError(400, { phone: ["Number already in use."] }));
    openEditor();
    fireEvent.change(phoneInput(), { target: { value: "+255712345678" } });
    save();

    await waitFor(() => expect(screen.getByText("Number already in use.")).toBeTruthy());
  });
});
