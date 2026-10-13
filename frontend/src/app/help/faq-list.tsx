"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { inputClassName } from "@/components/ui/form-field";

export type FaqItem = { q: string; a: string };
export type FaqSection = { id: string; title: string; items: FaqItem[] };

function matches(item: FaqItem, query: string) {
  return item.q.toLowerCase().includes(query) || item.a.toLowerCase().includes(query);
}

export function FaqList({ sections }: { sections: FaqSection[] }) {
  const [query, setQuery] = useState("");
  const needle = query.trim().toLowerCase();

  const visible = sections
    .map((section) => ({
      ...section,
      items: needle ? section.items.filter((item) => matches(item, needle)) : section.items,
    }))
    .filter((section) => section.items.length > 0);

  return (
    <div className="flex flex-col gap-6">
      <input
        type="search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search questions — e.g. payment, delivery, refund"
        aria-label="Search help articles"
        className={`${inputClassName} w-full`}
      />

      {!needle && (
        <nav aria-label="Help topics" className="flex flex-wrap gap-2">
          {sections.map((section) => (
            <a
              key={section.id}
              href={`#${section.id}`}
              className="rounded-full border border-border bg-card px-3 py-1 text-xs font-medium text-text-primary transition-colors hover:border-teal-400 hover:text-brand-text"
            >
              {section.title}
            </a>
          ))}
        </nav>
      )}

      {visible.length === 0 ? (
        <Card variant="muted" className="text-sm text-text-muted">
          No answers match &ldquo;{query.trim()}&rdquo;. Try another word, or contact our support
          team below — we&apos;re happy to help.
        </Card>
      ) : (
        visible.map((section) => (
          <section key={section.id} id={section.id} className="flex scroll-mt-24 flex-col gap-3">
            <h2 className="text-lg font-semibold text-text-primary">{section.title}</h2>
            <div className="flex flex-col gap-2">
              {section.items.map((item) => (
                <Card key={item.q} as="details" padding="none" className="group">
                  <summary className="flex cursor-pointer list-none items-center justify-between gap-4 px-4 py-3 text-sm font-medium text-text-primary [&::-webkit-details-marker]:hidden">
                    {item.q}
                    <span
                      aria-hidden
                      className="shrink-0 text-lg leading-none text-text-muted transition-transform group-open:rotate-45"
                    >
                      +
                    </span>
                  </summary>
                  <p className="px-4 pb-4 text-sm leading-relaxed text-text-muted">{item.a}</p>
                </Card>
              ))}
            </div>
          </section>
        ))
      )}
    </div>
  );
}
