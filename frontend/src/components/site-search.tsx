"use client";

import { useEffect, useId, useState } from "react";
import { useRouter } from "next/navigation";
import {
  listProducts,
  listPublicShops,
  listServices,
  type CatalogProduct,
  type CatalogService,
  type CatalogShopListItem,
} from "@/lib/api-client";
import { ShopLogo } from "@/components/shop-logo";
import { inputClassName } from "@/components/ui/form-field";
import { cn } from "@/lib/cn";
import { formatCurrency } from "@/lib/currency";

const SEARCH_DEBOUNCE_MS = 300;
export const MIN_QUERY_LENGTH = 2;
const PRODUCT_LIMIT = 5;
const SERVICE_LIMIT = 4;
const SHOP_LIMIT = 3;

type Suggestions = {
  products: CatalogProduct[];
  services: CatalogService[];
  shops: CatalogShopListItem[];
};

type Status = "idle" | "loading" | "done" | "error";

/** One row of the suggestion list. Rows are numbered across all groups for keyboard focus. */
type Option = { key: string; href: string };

export function searchHref(query: string): string {
  return `/search?q=${encodeURIComponent(query.trim())}`;
}

function value<T>(result: PromiseSettledResult<{ results: T[] }>, limit: number): T[] {
  return result.status === "fulfilled" ? result.value.results.slice(0, limit) : [];
}

/** Site-wide search box: suggests matching products, services and shops as the customer types,
 * and Enter (with nothing highlighted) opens the full results page. */
export function SiteSearch({
  initialQuery = "",
  autoFocus = false,
  onNavigate,
  onEscape,
  className,
}: {
  initialQuery?: string;
  autoFocus?: boolean;
  /** Called after a suggestion or the results page is opened, e.g. to close a menu. */
  onNavigate?: () => void;
  /** Called when Escape is pressed with no suggestion list open. */
  onEscape?: () => void;
  className?: string;
}) {
  const router = useRouter();
  const id = useId();
  const listId = `${id}-results`;
  const [query, setQuery] = useState(initialQuery);
  // The latest finished lookup, tagged with the query it answered.
  const [result, setResult] = useState<{
    query: string;
    suggestions: Suggestions | null;
    failed: boolean;
  } | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [active, setActive] = useState(-1);
  // Don't suggest for text that was prefilled (e.g. on the results page) until it's edited.
  const [typed, setTyped] = useState(false);

  const trimmed = query.trim();
  const searchable = trimmed.length >= MIN_QUERY_LENGTH;
  const status: Status =
    !typed || !searchable
      ? "idle"
      : result?.query !== trimmed
        ? "loading"
        : result.failed
          ? "error"
          : "done";
  // While a new lookup runs, keep showing the previous matches instead of flashing empty.
  const suggestions = status === "idle" ? null : (result?.suggestions ?? null);

  useEffect(() => {
    if (!typed || !searchable) return;
    let cancelled = false;
    const timer = setTimeout(() => {
      Promise.allSettled([
        listProducts({ q: trimmed, limit: PRODUCT_LIMIT }),
        listServices({ search: trimmed }),
        listPublicShops(1, trimmed),
      ]).then(([products, services, shops]) => {
        if (cancelled) return;
        // One failing source shouldn't hide the others; only all failing is an error.
        const failed = [products, services, shops].every((r) => r.status === "rejected");
        setResult({
          query: trimmed,
          failed,
          suggestions: failed
            ? null
            : {
                products: value(products, PRODUCT_LIMIT),
                services: value(services, SERVICE_LIMIT),
                shops: value(shops, SHOP_LIMIT),
              },
        });
        setActive(-1);
      });
    }, SEARCH_DEBOUNCE_MS);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [trimmed, searchable, typed]);

  const options: Option[] = [
    ...(suggestions?.products ?? []).map((p) => ({
      key: `product-${p.id}`,
      href: `/products/${p.id}`,
    })),
    ...(suggestions?.services ?? []).map((s) => ({
      key: `service-${s.id}`,
      href: `/services/${s.id}`,
    })),
    ...(suggestions?.shops ?? []).map((s) => ({ key: `shop-${s.id}`, href: `/shops/${s.id}` })),
  ];
  if (searchable) options.push({ key: "all", href: searchHref(trimmed) });
  const indexOf = (key: string) => options.findIndex((option) => option.key === key);
  const showList = isOpen && searchable && typed && status !== "idle";
  const hasMatches = options.length > 1;

  function go(href: string) {
    setTyped(false);
    setIsOpen(false);
    setActive(-1);
    (document.activeElement as HTMLElement | null)?.blur();
    router.push(href);
    onNavigate?.();
  }

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (active >= 0 && options[active]) go(options[active].href);
    else if (trimmed) go(searchHref(trimmed));
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Escape") {
      if (isOpen && trimmed) setIsOpen(false);
      else onEscape?.();
      return;
    }
    if (!showList || options.length === 0) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive((index) => (index + 1) % options.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((index) => (index <= 0 ? options.length - 1 : index - 1));
    }
  }

  function rowProps(key: string, href: string) {
    const index = indexOf(key);
    return {
      id: `${listId}-${index}`,
      selected: index === active,
      onPick: () => go(href),
    };
  }

  return (
    <form role="search" onSubmit={handleSubmit} className={cn("relative", className)}>
      <label htmlFor={id} className="sr-only">
        Search products, services and shops
      </label>
      <svg
        viewBox="0 0 20 20"
        fill="none"
        stroke="currentColor"
        strokeWidth={1.6}
        strokeLinecap="round"
        className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted"
        aria-hidden
      >
        <circle cx="9" cy="9" r="5.5" />
        <path d="M13 13l4 4" />
      </svg>
      <input
        autoFocus={autoFocus}
        id={id}
        type="search"
        enterKeyHint="search"
        autoComplete="off"
        role="combobox"
        aria-expanded={showList}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={showList && active >= 0 ? `${listId}-${active}` : undefined}
        placeholder="Search products, services and shops…"
        value={query}
        onChange={(e) => {
          setTyped(true);
          setIsOpen(true);
          setActive(-1);
          setQuery(e.target.value);
        }}
        onFocus={() => setIsOpen(true)}
        onBlur={() => setIsOpen(false)}
        onKeyDown={handleKeyDown}
        className={cn(
          inputClassName,
          "w-full pl-9 pr-9 [&::-webkit-search-cancel-button]:appearance-none",
        )}
      />
      {query && (
        <button
          type="button"
          aria-label="Clear search"
          onMouseDown={(e) => e.preventDefault()}
          onClick={() => {
            setQuery("");
            setActive(-1);
            document.getElementById(id)?.focus();
          }}
          className="absolute right-2 top-1/2 flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded-full text-text-muted hover:bg-hover hover:text-text-primary"
        >
          <svg viewBox="0 0 20 20" className="h-3.5 w-3.5" aria-hidden>
            <path
              d="M5 5l10 10M15 5L5 15"
              stroke="currentColor"
              strokeWidth={1.8}
              strokeLinecap="round"
            />
          </svg>
        </button>
      )}

      {showList && (
        <div className="absolute inset-x-0 top-full z-20 mt-1 max-h-[70vh] overflow-y-auto rounded-control border border-border bg-card py-1 shadow-lg">
          <ul id={listId} role="listbox" aria-label="Search suggestions">
            {status === "loading" && !suggestions && (
              <li className="px-3 py-2 text-sm text-text-muted">Searching…</li>
            )}
            {status === "error" && (
              <li className="px-3 py-2 text-sm text-text-muted">
                Search isn&apos;t available right now. Press Enter to try the results page.
              </li>
            )}
            {status === "done" && !hasMatches && (
              <li className="px-3 py-2 text-sm text-text-muted">
                No matches for &ldquo;{trimmed}&rdquo;.
              </li>
            )}

            {suggestions && suggestions.products.length > 0 && (
              <SuggestionGroup label="Products">
                {suggestions.products.map((product) => (
                  <SuggestionRow
                    key={product.id}
                    {...rowProps(`product-${product.id}`, `/products/${product.id}`)}
                  >
                    {product.thumbnail_url ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={product.thumbnail_url}
                        alt=""
                        className="h-9 w-9 shrink-0 rounded-control object-cover"
                      />
                    ) : (
                      <span className="h-9 w-9 shrink-0 rounded-control bg-card-muted" />
                    )}
                    <span className="flex min-w-0 flex-1 flex-col leading-tight">
                      <span className="truncate font-medium text-text-primary">{product.name}</span>
                      <span className="truncate text-xs text-text-muted">{product.shop_name}</span>
                    </span>
                    <span className="shrink-0 text-xs font-medium text-text-primary">
                      {formatCurrency(product.price)}
                    </span>
                  </SuggestionRow>
                ))}
              </SuggestionGroup>
            )}

            {suggestions && suggestions.services.length > 0 && (
              <SuggestionGroup label="Services">
                {suggestions.services.map((service) => (
                  <SuggestionRow
                    key={service.id}
                    {...rowProps(`service-${service.id}`, `/services/${service.id}`)}
                  >
                    <ShopLogo url={service.shop.logo_url} name={service.shop.name} size="sm" />
                    <span className="flex min-w-0 flex-1 flex-col leading-tight">
                      <span className="truncate font-medium text-text-primary">{service.name}</span>
                      <span className="truncate text-xs text-text-muted">{service.shop.name}</span>
                    </span>
                    <span className="shrink-0 text-xs font-medium text-text-primary">
                      {formatCurrency(service.price)}
                    </span>
                  </SuggestionRow>
                ))}
              </SuggestionGroup>
            )}

            {suggestions && suggestions.shops.length > 0 && (
              <SuggestionGroup label="Shops">
                {suggestions.shops.map((shop) => (
                  <SuggestionRow
                    key={shop.id}
                    {...rowProps(`shop-${shop.id}`, `/shops/${shop.id}`)}
                  >
                    <ShopLogo url={shop.logo_url} name={shop.name} size="sm" />
                    <span className="flex min-w-0 flex-1 flex-col leading-tight">
                      <span className="truncate font-medium text-text-primary">{shop.name}</span>
                      <span className="text-xs text-text-muted">
                        {shop.business_type === "SERVICES" ? "Services" : "Products"}
                      </span>
                    </span>
                  </SuggestionRow>
                ))}
              </SuggestionGroup>
            )}

            {status !== "loading" || suggestions ? (
              <SuggestionRow
                {...rowProps("all", searchHref(trimmed))}
                className="mt-1 border-t border-border font-medium text-text-primary"
              >
                See all results for &ldquo;{trimmed}&rdquo; →
              </SuggestionRow>
            ) : null}
          </ul>
        </div>
      )}
    </form>
  );
}

function SuggestionGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <li role="presentation">
      <p className="px-3 pb-1 pt-2 text-[11px] font-semibold uppercase tracking-wider text-text-muted">
        {label}
      </p>
      <ul role="group" aria-label={label}>
        {children}
      </ul>
    </li>
  );
}

function SuggestionRow({
  id,
  selected,
  onPick,
  className,
  children,
}: {
  id: string;
  selected: boolean;
  onPick: () => void;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <li
      id={id}
      role="option"
      aria-selected={selected}
      // mousedown, not click: it fires before the input's blur closes the list.
      onMouseDown={(e) => {
        e.preventDefault();
        onPick();
      }}
      className={cn(
        // Hover only tints the row; Enter follows the keyboard highlight, not the pointer.
        "flex cursor-pointer items-center gap-3 px-3 py-2 text-sm hover:bg-hover",
        selected && "bg-card-muted",
        className,
      )}
    >
      {children}
    </li>
  );
}
