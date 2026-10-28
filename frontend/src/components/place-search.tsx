"use client";

import { useEffect, useId, useRef, useState } from "react";
import { searchPlaces, type Place } from "@/lib/geo";
import { inputClassName } from "@/components/ui/form-field";

const SEARCH_DEBOUNCE_MS = 350;
const MIN_QUERY_LENGTH = 3;

/** A free-text address box that suggests matching places in Dar es Salaam as the customer
 * types. Picking a suggestion hands its pin to `onSelect` so the map can jump there; whatever
 * is typed (e.g. a house number or landmark) is still kept as the address text. */
export function PlaceSearch({
  label,
  value,
  onChange,
  onSelect,
  error,
}: {
  label: string;
  value: string;
  onChange: (text: string) => void;
  onSelect: (place: Place) => void;
  error?: string;
}) {
  const id = useId();
  const listId = `${id}-places`;
  const [places, setPlaces] = useState<Place[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const [searchFailed, setSearchFailed] = useState(false);
  // Only search for what the customer typed, not text filled in by picking a place or pin.
  const typedRef = useRef(false);

  useEffect(() => {
    const query = value.trim();
    if (!typedRef.current || query.length < MIN_QUERY_LENGTH) {
      setPlaces([]);
      return;
    }
    const controller = new AbortController();
    const timer = setTimeout(() => {
      searchPlaces(query, controller.signal)
        .then((results) => {
          setPlaces(results);
          setActive(-1);
          setSearchFailed(false);
        })
        .catch(() => {
          if (controller.signal.aborted) return;
          setPlaces([]);
          setSearchFailed(true);
        });
    }, SEARCH_DEBOUNCE_MS);
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [value]);

  function choose(place: Place) {
    typedRef.current = false;
    setIsOpen(false);
    setPlaces([]);
    onSelect(place);
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (!isOpen || places.length === 0) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive((index) => (index + 1) % places.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((index) => (index <= 0 ? places.length - 1 : index - 1));
    } else if (event.key === "Enter" && active >= 0) {
      // Pick the highlighted place instead of submitting the checkout form.
      event.preventDefault();
      choose(places[active]);
    } else if (event.key === "Escape") {
      setIsOpen(false);
    }
  }

  const showList = isOpen && places.length > 0;

  return (
    <div className="flex flex-col gap-1 text-sm font-medium text-text-primary">
      <label htmlFor={id}>{label}</label>
      <div className="relative">
        <input
          id={id}
          type="text"
          required
          autoComplete="off"
          role="combobox"
          aria-expanded={showList}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={showList && active >= 0 ? `${listId}-${active}` : undefined}
          placeholder="Search a street, area or landmark, e.g. Kariakoo"
          value={value}
          onChange={(e) => {
            typedRef.current = true;
            setIsOpen(true);
            onChange(e.target.value);
          }}
          onFocus={() => setIsOpen(true)}
          onBlur={() => setIsOpen(false)}
          onKeyDown={handleKeyDown}
          className={`${inputClassName} w-full`}
        />
        {showList && (
          <ul
            id={listId}
            role="listbox"
            className="absolute inset-x-0 top-full z-10 mt-1 overflow-hidden rounded-control border border-border bg-card shadow-lg"
          >
            {places.map((place, index) => (
              <li
                key={`${place.label}-${index}`}
                id={`${listId}-${index}`}
                role="option"
                aria-selected={index === active}
                // mousedown, not click: it fires before the input's blur closes the list.
                onMouseDown={(e) => {
                  e.preventDefault();
                  choose(place);
                }}
                onMouseEnter={() => setActive(index)}
                className={`cursor-pointer px-3 py-2 font-normal ${
                  index === active ? "bg-card-muted" : ""
                }`}
              >
                {place.label}
              </li>
            ))}
          </ul>
        )}
      </div>
      <span className="text-xs font-normal text-text-muted">
        {searchFailed
          ? "Place search isn't available right now. Type your address and drop the pin on the map."
          : "Pick a suggestion to jump the map there, then add a house number or landmark if needed."}
      </span>
      {error && <span className="text-xs text-status-cancelled">{error}</span>}
    </div>
  );
}
