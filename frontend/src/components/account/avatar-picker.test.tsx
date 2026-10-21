import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { AvatarPicker } from "./avatar-picker";
import type { AuthUser } from "@/lib/auth-context";
import { MAX_AVATAR_SIZE_BYTES } from "@/lib/profile";

const refreshUser = vi.fn();
const uploadMyAvatar = vi.fn();

vi.mock("@/lib/auth-context", () => ({ useAuth: () => ({ refreshUser }) }));
vi.mock("@/lib/api-client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api-client")>()),
  uploadMyAvatar: (...args: unknown[]) => uploadMyAvatar(...args),
}));

const USER = { name: "Asha Mwita", avatar_url: null } as AuthUser;

beforeEach(() => {
  refreshUser.mockResolvedValue(undefined);
  uploadMyAvatar.mockResolvedValue(undefined);
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

function pick(file: File) {
  fireEvent.change(screen.getByTestId("avatar-input"), { target: { files: [file] } });
}

describe("AvatarPicker", () => {
  it("rejects a photo over 2MB without uploading", () => {
    render(<AvatarPicker user={USER} />);
    pick(new File([new Uint8Array(MAX_AVATAR_SIZE_BYTES + 1)], "big.png", { type: "image/png" }));

    expect(screen.getByText("big.png is over 2MB.")).toBeTruthy();
    expect(uploadMyAvatar).not.toHaveBeenCalled();
  });

  it("rejects a non-image file", () => {
    render(<AvatarPicker user={USER} />);
    pick(new File(["hello"], "notes.txt", { type: "text/plain" }));

    expect(screen.getByText("notes.txt is not an image.")).toBeTruthy();
    expect(uploadMyAvatar).not.toHaveBeenCalled();
  });

  it("uploads a valid photo and refreshes the profile", async () => {
    render(<AvatarPicker user={USER} />);
    const file = new File(["png"], "me.png", { type: "image/png" });
    pick(file);

    await waitFor(() => expect(refreshUser).toHaveBeenCalled());
    expect(uploadMyAvatar).toHaveBeenCalledWith(file);
  });
});
