"use client";

import { useCallback, useEffect, useState } from "react";
import { ShopLogo } from "@/components/shop-logo";
import Link from "next/link";
import { listCategories, listProducts, type CatalogProduct, type Category } from "@/lib/api-client";
import { StarRating } from "@/components/star-rating";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/cn";
import { formatCurrency } from "@/lib/currency";

const AUTOPLAY_MS = 5000;
// Newest products to sample — the catalog API caps page_size at 24.
const PRODUCT_SAMPLE_SIZE = 24;
const MAX_SLIDES = 5;
const PRODUCTS_PER_SLIDE = 2;

const THEMES = [
  {
    gradient:
      "from-teal-50/80 via-emerald-50/40 to-white dark:from-teal-900/40 dark:via-card dark:to-card",
    badge: "bg-emerald-500",
  },
  {
    gradient:
      "from-amber-50/80 via-orange-50/30 to-white dark:from-amber-900/30 dark:via-card dark:to-card",
    badge: "bg-amber-500",
  },
  {
    gradient:
      "from-sky-50 via-indigo-50/30 to-white dark:from-sky-900/40 dark:via-card dark:to-card",
    badge: "bg-navy-900",
  },
  {
    gradient:
      "from-rose-50/80 via-pink-50/30 to-white dark:from-rose-900/30 dark:via-card dark:to-card",
    badge: "bg-rose-500",
  },
] as const;

export type CategorySlide = {
  category: Category;
  productCount: number;
  shopCount: number;
  products: CatalogProduct[];
};

function byRating(a: CatalogProduct, b: CatalogProduct): number {
  const ratingDiff = (b.average_rating ?? -1) - (a.average_rating ?? -1);
  return ratingDiff !== 0 ? ratingDiff : b.review_count - a.review_count;
}

/** One slide per top-level category that has products in the sample (subcategory products
 * count toward their parent), busiest categories first. */
export function buildSlides(categories: Category[], products: CatalogProduct[]): CategorySlide[] {
  const topLevelSlug = new Map<string, string>();
  for (const category of categories) {
    topLevelSlug.set(category.slug, category.slug);
    for (const child of category.children ?? []) topLevelSlug.set(child.slug, category.slug);
  }

  const bySlug = new Map<string, CatalogProduct[]>();
  for (const product of products) {
    const slug = product.category && topLevelSlug.get(product.category);
    if (!slug) continue;
    const group = bySlug.get(slug) ?? [];
    group.push(product);
    bySlug.set(slug, group);
  }

  return categories
    .filter((category) => bySlug.has(category.slug))
    .map((category) => {
      const group = bySlug.get(category.slug)!;
      return {
        category,
        productCount: group.length,
        shopCount: new Set(group.map((p) => p.shop_name)).size,
        products: [...group].sort(byRating).slice(0, PRODUCTS_PER_SLIDE),
      };
    })
    .sort((a, b) => b.productCount - a.productCount)
    .slice(0, MAX_SLIDES);
}

function plural(count: number, word: string): string {
  return `${count} ${word}${count === 1 ? "" : "s"}`;
}

function useCategorySlides(): CategorySlide[] {
  const [slides, setSlides] = useState<CategorySlide[]>([]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [categories, products] = await Promise.all([
          listCategories(),
          listProducts(PRODUCT_SAMPLE_SIZE),
        ]);
        if (!cancelled) setSlides(buildSlides(categories, products.results));
      } catch {
        // non-fatal — the homepage still works without the slideshow
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  return slides;
}

export function PromoSlideshow() {
  const slides = useCategorySlides();
  const [current, setCurrent] = useState(0);
  const [paused, setPaused] = useState(false);
  const total = slides.length;
  const active = total > 0 ? current % total : 0;

  const goTo = useCallback((index: number) => setCurrent((index + total) % total), [total]);

  // Depends on `current` so any manual navigation restarts the autoplay timer.
  useEffect(() => {
    if (paused || total < 2) return;
    const id = setInterval(() => setCurrent((i) => (i + 1) % total), AUTOPLAY_MS);
    return () => clearInterval(id);
  }, [paused, current, total]);

  if (total === 0) return null;

  return (
    <Card
      as="section"
      padding="none"
      aria-roledescription="carousel"
      aria-label="Shop by category"
      className="relative overflow-hidden border border-border"
    >
      <div className="flex items-center justify-between gap-3 overflow-x-auto border-b border-border bg-card-muted px-6 py-3 text-xs font-medium sm:text-sm">
        <div className="flex items-center gap-2" role="tablist" aria-label="Categories">
          {slides.map((slide, index) => (
            <button
              key={slide.category.slug}
              type="button"
              role="tab"
              aria-selected={index === active}
              onClick={() => goTo(index)}
              className={cn(
                "whitespace-nowrap rounded-pill px-3.5 py-1.5 transition",
                index === active
                  ? "bg-navy-900 font-semibold text-text-inverse shadow-card"
                  : "text-text-muted hover:bg-card hover:text-text-primary",
              )}
            >
              {slide.category.name}
            </button>
          ))}
        </div>
        {total > 1 && (
          <div className="flex items-center gap-1">
            <ArrowButton
              label="Previous slide"
              onClick={() => goTo(active - 1)}
              path="M15 19l-7-7 7-7"
            />
            <ArrowButton label="Next slide" onClick={() => goTo(active + 1)} path="M9 5l7 7-7 7" />
          </div>
        )}
      </div>

      <div
        className="grid [&>*]:col-start-1 [&>*]:row-start-1"
        onMouseEnter={() => setPaused(true)}
        onMouseLeave={() => setPaused(false)}
      >
        {slides.map((slide, index) => {
          const isActive = index === active;
          const theme = THEMES[index % THEMES.length];
          return (
            <article
              key={slide.category.slug}
              aria-roledescription="slide"
              aria-label={`${index + 1} of ${total}`}
              aria-hidden={!isActive}
              inert={!isActive}
              className={cn(
                "flex flex-col items-center justify-between gap-8 bg-gradient-to-r p-6 transition duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] motion-reduce:transition-none sm:p-8 lg:flex-row lg:p-10",
                theme.gradient,
                isActive ? "scale-100 opacity-100" : "pointer-events-none scale-[0.98] opacity-0",
              )}
            >
              <div className="max-w-xl space-y-4 text-left">
                <div className="flex flex-wrap items-center gap-2.5">
                  <span
                    className={cn(
                      "rounded-pill px-3 py-1 text-xs font-bold uppercase tracking-wide text-white",
                      theme.badge,
                    )}
                  >
                    Category
                  </span>
                  <span className="text-xs font-medium text-text-muted">
                    {plural(slide.productCount, "product")} from{" "}
                    {plural(slide.shopCount, "independent shop")}
                  </span>
                </div>
                <h2 className="text-2xl font-extrabold leading-tight tracking-tight text-text-primary sm:text-3xl lg:text-4xl">
                  Shop {slide.category.name}
                </h2>
                <p className="text-sm leading-relaxed text-text-muted sm:text-base">
                  Fresh picks from independent sellers on E-Mall.
                </p>
                <div className="pt-2">
                  <Link
                    href={`/products?category=${encodeURIComponent(slide.category.slug)}`}
                    className="inline-block rounded-pill bg-navy-900 px-6 py-3 text-sm font-semibold text-on-primary shadow-card transition hover:bg-navy-800 hover:shadow-card-hover"
                  >
                    Browse {slide.category.name} →
                  </Link>
                </div>
              </div>
              <ul className="grid w-full grid-cols-2 gap-3.5 lg:w-auto">
                {slide.products.map((product) => (
                  <ProductTile key={product.id} product={product} />
                ))}
              </ul>
            </article>
          );
        })}
      </div>

      {total > 1 && (
        <div className="flex items-center justify-center gap-2 border-t border-border bg-card-muted py-2.5">
          {slides.map((slide, index) => (
            <button
              key={slide.category.slug}
              type="button"
              aria-label={`Go to slide ${index + 1}`}
              aria-current={index === active}
              onClick={() => goTo(index)}
              className={cn(
                "h-2 rounded-full transition-all",
                index === active
                  ? "w-6 bg-navy-900"
                  : "w-2 bg-text-muted/40 hover:bg-text-muted/60",
              )}
            />
          ))}
        </div>
      )}
    </Card>
  );
}

function ProductTile({ product }: { product: CatalogProduct }) {
  return (
    <li className="w-40 sm:w-44">
      <Link
        href={`/products/${product.id}`}
        className="flex h-full flex-col gap-1.5 rounded-card border border-border bg-card/95 p-3 shadow-card transition-shadow hover:shadow-card-hover"
      >
        {product.thumbnail_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={product.thumbnail_url}
            alt={product.name}
            className="aspect-square w-full rounded-control object-cover"
          />
        ) : (
          <div className="flex aspect-square w-full items-center justify-center rounded-control bg-card-muted text-sm text-text-muted">
            No image
          </div>
        )}
        <p className="line-clamp-2 text-sm font-semibold text-text-primary">{product.name}</p>
        <p className="flex items-center gap-1 text-xs text-text-muted">
          <ShopLogo url={product.shop_logo_url} name={product.shop_name} size="xs" />
          {product.shop_name}
        </p>
        <p className="text-sm font-bold text-text-primary">{formatCurrency(product.price)}</p>
        <StarRating rating={product.average_rating} reviewCount={product.review_count} />
      </Link>
    </li>
  );
}

function ArrowButton({
  label,
  onClick,
  path,
}: {
  label: string;
  onClick: () => void;
  path: string;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      className="flex h-8 w-8 items-center justify-center rounded-full border border-border bg-card text-text-muted transition hover:bg-card-muted"
    >
      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
        <path d={path} strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} />
      </svg>
    </button>
  );
}
