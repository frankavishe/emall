import type { Metadata } from "next";
import Link from "next/link";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export const metadata: Metadata = {
  title: "About Us | MangiMall",
  description:
    "Meet Frank Kavishe, Founder & CEO of MangiMall, and learn how we're reimagining the way malls work.",
};

const PILLARS = [
  {
    title: "The mall, reimagined",
    body: "Every shop open 24/7 and browsable from any phone — no walls, no parking, no closing time.",
  },
  {
    title: "Empowering local vendors",
    body: "Independent sellers get shop approval, product listings, and order tools to reach customers nationwide.",
  },
  {
    title: "Payments that fit Tanzania",
    body: "Checkout with M-Pesa, Tigo Pesa, Airtel Money, or card — the way people already pay.",
  },
  {
    title: "Trust by design",
    body: "Verified shops, honest reviews, and buyer protection so every purchase feels safe.",
  },
];

export default function AboutPage() {
  return (
    <PageShell size="lg">
      <Card variant="hero" className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold">About MangiMall</h1>
        <p className="text-sm text-text-inverse/70">
          Bringing the whole mall to your phone — every shop, one trusted marketplace.
        </p>
      </Card>

      <Card className="flex flex-col gap-6 sm:flex-row sm:items-start">
        <div
          aria-hidden
          className="flex h-20 w-20 shrink-0 items-center justify-center rounded-full bg-navy-900 text-2xl font-bold text-teal-400"
        >
          FK
        </div>
        <div className="flex flex-col gap-3">
          <div>
            <h2 className="text-xl font-semibold text-text-primary">Frank Kavishe</h2>
            <p className="text-sm font-medium text-brand-text">Founder &amp; CEO, MangiMall</p>
          </div>
          <p className="text-sm leading-relaxed text-text-muted">
            Frank Kavishe is a technologist who wants to revolutionize the way malls work. He
            believes a mall shouldn&apos;t be limited by walls, parking, or opening hours — it
            should live wherever customers are. Frank founded MangiMall to bring independent shops
            and local dealers online under one trusted roof, giving them the reach of a large
            retailer without the cost of a storefront.
          </p>
          <p className="text-sm leading-relaxed text-text-muted">
            With a background in building software and a passion for Tanzania&apos;s growing digital
            economy, Frank leads MangiMall&apos;s product and technology vision: seamless
            mobile-money checkout, real-time order tracking, and tools that let any vendor launch a
            shop in minutes.
          </p>
        </div>
      </Card>

      <section className="flex flex-col gap-4">
        <h2 className="text-lg font-semibold text-text-primary">What we&apos;re building</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {PILLARS.map((pillar) => (
            <Card key={pillar.title} variant="muted" padding="sm" className="flex flex-col gap-1">
              <h3 className="text-sm font-semibold text-text-primary">{pillar.title}</h3>
              <p className="text-sm text-text-muted">{pillar.body}</p>
            </Card>
          ))}
        </div>
      </section>

      <Card variant="hero" className="flex flex-col gap-4">
        <blockquote className="text-lg font-medium leading-snug">
          &ldquo;Technology should make shopping local, not just convenient.&rdquo;
          <footer className="mt-2 text-sm font-normal text-text-inverse/70">
            — Frank Kavishe, Founder &amp; CEO
          </footer>
        </blockquote>
        <div className="flex flex-wrap gap-3">
          <Button variant="primary" className="bg-teal-400 text-navy-900 hover:bg-teal-300" asChild>
            <Link href="/products">Browse products</Link>
          </Button>
          <Button variant="secondary" asChild>
            <Link href="/register">Open a shop</Link>
          </Button>
        </div>
      </Card>
    </PageShell>
  );
}
