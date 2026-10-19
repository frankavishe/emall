import type { Metadata } from "next";
import Link from "next/link";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Pill, statusToTone } from "@/components/ui/pill";
import { TrackLinkForm } from "./track-link-form";

export const metadata: Metadata = {
  title: "Track Your Order | MangiMall",
  description:
    "Follow your MangiMall order from payment to doorstep: open My Orders, or use the private tracking link from your order confirmation email.",
};

const STATUSES: { status: string; label: string; meaning: string }[] = [
  {
    status: "AWAITING_PAYMENT",
    label: "Awaiting payment",
    meaning:
      "We're waiting for your payment to be confirmed: approve the prompt on your phone, or (for Lipa Namba) our team is checking your transaction ID.",
  },
  {
    status: "PAYMENT_FAILED",
    label: "Payment failed",
    meaning:
      "The payment didn't go through. Your order isn't lost — you can try paying again from the order page.",
  },
  {
    status: "PENDING",
    label: "Pending",
    meaning: "The shop has received your item and will start preparing it shortly.",
  },
  {
    status: "PROCESSING",
    label: "Processing",
    meaning: "The shop is preparing your item for pickup.",
  },
  {
    status: "SHIPPED",
    label: "Shipped",
    meaning: "A MangiMall rider has picked up your item and is on the way to you.",
  },
  {
    status: "DELIVERED",
    label: "Delivered",
    meaning: "Your item has arrived. Enjoy — and leave a review on the product page!",
  },
  {
    status: "CANCELLED",
    label: "Cancelled",
    meaning: "The item was cancelled. Contact support if you weren't expecting this.",
  },
];

export default function TrackOrderPage() {
  return (
    <PageShell size="md">
      <Card variant="hero" className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold">Track Your Order</h1>
        <p className="text-sm text-text-inverse/70">
          Follow every item from the shop to your door. Items from different shops travel
          separately, so each one has its own status.
        </p>
      </Card>

      <div className="grid gap-6 md:grid-cols-2">
        <Card className="flex flex-col gap-3">
          <h2 className="text-lg font-semibold">Have an account?</h2>
          <p className="text-sm text-text-muted">
            Sign in and open My Orders to see all your orders and live status updates. We also
            email you whenever an item&apos;s status changes.
          </p>
          <Button asChild className="mt-auto self-start">
            <Link href="/orders">Go to My Orders</Link>
          </Button>
        </Card>

        <Card className="flex flex-col gap-3">
          <h2 className="text-lg font-semibold">Checked out as a guest?</h2>
          <p className="text-sm text-text-muted">
            Your order confirmation email has a private tracking link. Open it, or paste it here.
          </p>
          <TrackLinkForm />
        </Card>
      </div>

      <Card className="flex flex-col gap-4">
        <h2 className="text-lg font-semibold">What each status means</h2>
        <ul className="flex flex-col gap-3">
          {STATUSES.map(({ status, label, meaning }) => (
            <li key={status} className="flex flex-col gap-1 sm:flex-row sm:items-start sm:gap-4">
              <span className="shrink-0 sm:w-36">
                <Pill tone={statusToTone(status)}>{label}</Pill>
              </span>
              <p className="text-sm text-text-muted">{meaning}</p>
            </li>
          ))}
        </ul>
      </Card>

      <Card variant="hero" className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <h2 className="text-lg font-semibold">Can&apos;t find your link?</h2>
          <p className="text-sm text-text-inverse/70">
            Our support team is available every day, 8am – 10pm EAT. Share your order number and
            the email you checked out with, and we&apos;ll help you find your order. More answers
            in the{" "}
            <Link href="/help#orders" className="font-medium text-teal-400 hover:underline">
              Help Center
            </Link>
            .
          </p>
        </div>
        <ul className="flex flex-col gap-2 text-sm">
          <li>
            Call:{" "}
            <a href="tel:+255774861380" className="font-medium text-teal-400 hover:underline">
              +255 774 861 380
            </a>{" "}
            /{" "}
            <a href="tel:+255793403553" className="font-medium text-teal-400 hover:underline">
              +255 793 403 553
            </a>
          </li>
          <li>
            WhatsApp:{" "}
            <a
              href="https://wa.me/255774861380"
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-teal-400 hover:underline"
            >
              +255 774 861 380
            </a>
          </li>
          <li>
            Email:{" "}
            <a
              href="mailto:support@mangimall.com"
              className="font-medium text-teal-400 hover:underline"
            >
              support@mangimall.com
            </a>
          </li>
        </ul>
      </Card>
    </PageShell>
  );
}
