import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ShopNameEditor } from "./shop-name-editor";
import type { Shop } from "@/lib/auth-context";

const refreshUser = vi.fn();
const updateShopName = vi.fn();

vi.mock("@/lib/auth-context", () => ({ useAuth: () => ({ refreshUser }) }));
vi.mock("@/lib/api-client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api-client")>()),
  updateShopName: (...args: unknown[]) => updateShopName(...args),
}));

const SHOP: Shop = { id: "7", name: "Mlimani Books", status: "APPROVED", logo_url: null };

beforeEach(() => {
  refreshUser.mockResolvedValue(undefined);
  updateShopName.mockResolvedValue(undefined);
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

const saveButton = () => screen.getByRole("button", { name: "Save name" }) as HTMLButtonElement;

describe("ShopNameEditor", () => {
  it("prefills the current name with saving disabled", () => {
    render(<ShopNameEditor shop={SHOP} />);

    expect((screen.getByRole("textbox") as HTMLInputElement).value).toBe("Mlimani Books");
    expect(saveButton().disabled).toBe(true);
  });

  it("keeps saving disabled for a blank name", () => {
    render(<ShopNameEditor shop={SHOP} />);

    fireEvent.change(screen.getByRole("textbox"), { target: { value: "   " } });

    expect(saveButton().disabled).toBe(true);
  });

  it("saves the trimmed name and refreshes the profile", async () => {
    render(<ShopNameEditor shop={SHOP} />);

    fireEvent.change(screen.getByRole("textbox"), { target: { value: "  Mlimani Reads  " } });
    fireEvent.click(saveButton());

    await waitFor(() => expect(refreshUser).toHaveBeenCalled());
    expect(updateShopName).toHaveBeenCalledWith("7", "Mlimani Reads");
  });
});
