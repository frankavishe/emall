import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ShopDescriptionEditor } from "./shop-description-editor";
import type { Shop } from "@/lib/auth-context";

const refreshUser = vi.fn();
const updateShopDescription = vi.fn();

vi.mock("@/lib/auth-context", () => ({ useAuth: () => ({ refreshUser }) }));
vi.mock("@/lib/api-client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api-client")>()),
  updateShopDescription: (...args: unknown[]) => updateShopDescription(...args),
}));

const SHOP: Shop = { id: "7", name: "Mlimani Books", status: "APPROVED", logo_url: null };

beforeEach(() => {
  refreshUser.mockResolvedValue(undefined);
  updateShopDescription.mockResolvedValue(undefined);
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

const saveButton = () =>
  screen.getByRole("button", { name: "Save description" }) as HTMLButtonElement;

describe("ShopDescriptionEditor", () => {
  it("prefills the saved description and shows the character count", () => {
    render(<ShopDescriptionEditor shop={{ ...SHOP, description: "Used textbooks." }} />);

    expect((screen.getByRole("textbox") as HTMLTextAreaElement).value).toBe("Used textbooks.");
    expect(screen.getByText("15/1000")).toBeTruthy();
    expect(saveButton().disabled).toBe(true);
  });

  it("saves the trimmed text and refreshes the profile", async () => {
    render(<ShopDescriptionEditor shop={SHOP} />);

    fireEvent.change(screen.getByRole("textbox"), { target: { value: "  New books daily.  " } });
    fireEvent.click(saveButton());

    await waitFor(() => expect(refreshUser).toHaveBeenCalled());
    expect(updateShopDescription).toHaveBeenCalledWith("7", "New books daily.");
  });
});
