import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import type { CatalogProduct, Category } from "@/lib/api-client";
import { buildSlides, PromoSlideshow } from "./promo-slideshow";

vi.mock("@/lib/api-client", () => ({
  listCategories: vi.fn(),
  listProducts: vi.fn(),
}));

const api = await import("@/lib/api-client");
const listCategories = vi.mocked(api.listCategories);
const listProducts = vi.mocked(api.listProducts);

function product(overrides: Partial<CatalogProduct> & { id: number; category: string }): CatalogProduct {
  return {
    name: `Product ${overrides.id}`,
    price: "10000",
    in_stock: true,
    shop_name: "Shop A",
    thumbnail_url: null,
    average_rating: null,
    review_count: 0,
    ...overrides,
  };
}

const CATEGORIES: Category[] = [
  { name: "Books", slug: "books" },
  { name: "Beauty", slug: "beauty" },
  { name: "Electronics", slug: "electronics" },
];

const PRODUCTS: CatalogProduct[] = [
  product({ id: 1, category: "beauty", shop_name: "Shop A" }),
  product({ id: 2, category: "beauty", shop_name: "Shop B", average_rating: 4.5, review_count: 3 }),
  product({ id: 3, category: "beauty", shop_name: "Shop B", average_rating: 4.5, review_count: 9 }),
  product({ id: 4, category: "books", name: "Ledger Guide" }),
];

describe("buildSlides", () => {
  it("groups by category, skips empty ones and orders by product count", () => {
    const slides = buildSlides(CATEGORIES, PRODUCTS);
    expect(slides.map((s) => s.category.slug)).toEqual(["beauty", "books"]);
    expect(slides[0].productCount).toBe(3);
    expect(slides[0].shopCount).toBe(2);
  });

  it("features the best-rated products, breaking ties by review count", () => {
    const [beauty] = buildSlides(CATEGORIES, PRODUCTS);
    expect(beauty.products.map((p) => p.id)).toEqual([3, 2]);
  });

  it("caps the number of slides at 5", () => {
    const categories = Array.from({ length: 7 }, (_, i) => ({ name: `C${i}`, slug: `c${i}` }));
    const products = categories.map((c, i) => product({ id: i, category: c.slug }));
    expect(buildSlides(categories, products)).toHaveLength(5);
  });
});

function selectedTab() {
  return screen.getAllByRole("tab").find((tab) => tab.getAttribute("aria-selected") === "true");
}

async function renderLoaded() {
  render(<PromoSlideshow />);
  await act(async () => {
    await Promise.resolve();
  });
}

describe("PromoSlideshow", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    listCategories.mockResolvedValue(CATEGORIES);
    listProducts.mockResolvedValue({ count: 4, next: null, previous: null, results: PRODUCTS });
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it("shows one tab per category with products", async () => {
    await renderLoaded();
    expect(screen.getAllByRole("tab").map((t) => t.textContent)).toEqual(["Beauty", "Books"]);
    expect(selectedTab()?.textContent).toBe("Beauty");
  });

  it("links to the filtered catalog and to real product pages", async () => {
    await renderLoaded();
    expect(screen.getByRole("link", { name: /Browse Beauty/ }).getAttribute("href")).toBe(
      "/products?category=beauty",
    );
    expect(screen.getByRole("link", { name: /Product 3/ }).getAttribute("href")).toBe("/products/3");
    // Products on inactive slides are hidden from assistive tech.
    expect(screen.queryByRole("link", { name: /Ledger Guide/ })).toBeNull();
  });

  it("navigates with the arrows, tabs and dots", async () => {
    await renderLoaded();

    fireEvent.click(screen.getByRole("button", { name: "Next slide" }));
    expect(selectedTab()?.textContent).toBe("Books");

    fireEvent.click(screen.getByRole("button", { name: "Previous slide" }));
    expect(selectedTab()?.textContent).toBe("Beauty");

    fireEvent.click(screen.getByRole("tab", { name: "Books" }));
    expect(selectedTab()?.textContent).toBe("Books");

    fireEvent.click(screen.getByRole("button", { name: "Go to slide 1" }));
    expect(selectedTab()?.textContent).toBe("Beauty");
  });

  it("autoplays and pauses while hovered", async () => {
    await renderLoaded();
    const wrapper = screen.getByRole("heading", { name: "Shop Beauty" }).closest("article")!.parentElement!;

    fireEvent.mouseEnter(wrapper);
    act(() => {
      vi.advanceTimersByTime(15000);
    });
    expect(selectedTab()?.textContent).toBe("Beauty");

    fireEvent.mouseLeave(wrapper);
    act(() => {
      vi.advanceTimersByTime(5000);
    });
    expect(selectedTab()?.textContent).toBe("Books");
  });

  it("renders nothing when the catalog request fails", async () => {
    listProducts.mockRejectedValue(new Error("network down"));
    await renderLoaded();
    expect(screen.queryByRole("tablist")).toBeNull();
  });

  it("renders nothing when there are no products", async () => {
    listProducts.mockResolvedValue({ count: 0, next: null, previous: null, results: [] });
    await renderLoaded();
    expect(screen.queryByRole("tablist")).toBeNull();
  });
});
