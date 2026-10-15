import type { Metadata } from "next";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { FaqList, type FaqSection } from "./faq-list";

export const metadata: Metadata = {
  title: "Help Center & FAQ | MangiMall",
  description:
    "Answers to common questions about ordering, mobile-money payments, delivery, refunds, your account, and selling on MangiMall.",
};

const FAQ_SECTIONS: FaqSection[] = [
  {
    id: "orders",
    title: "Orders & tracking",
    items: [
      {
        q: "How do I place an order?",
        a: "Browse products, add what you like to your cart, then go to checkout. Enter the recipient's name, phone number and address, drop a pin on the map where you want it delivered, review the delivery fee, and pay with mobile money.",
      },
      {
        q: "Can I buy from several shops in one order?",
        a: "Yes. Your cart can hold products from any number of shops and you pay once at checkout. Each shop prepares and sends its items separately, so items from different shops may arrive at different times.",
      },
      {
        q: "How do I track my order?",
        a: "Sign in and open My Orders. Each item shows its current status: Pending (received by the shop), Processing (being prepared), Shipped (picked up by a rider and on the way), Delivered, or Cancelled. We also email you whenever an item's status changes.",
      },
      {
        q: 'What do "Awaiting payment" and "Payment failed" mean?',
        a: "Awaiting payment means we're waiting for your payment to be confirmed: either you still need to approve the prompt on your phone, or (for Lipa Namba) our team is checking your transaction ID. Payment failed means the payment didn't go through — the order isn't lost, and you can try paying again from the order page.",
      },
      {
        q: "Can I cancel an order?",
        a: "Contact our support team as soon as possible with your order number. If the shop hasn't shipped the item yet, we'll work with them to cancel it.",
      },
    ],
  },
  {
    id: "payments",
    title: "Payments",
    items: [
      {
        q: "Which payment methods do you accept?",
        a: "You can pay cash on delivery, or pay by Lipa Namba from M-Pesa, Mixx by Yas (Tigo Pesa), Airtel Money, HaloPesa or AzamPesa. The options available to you are shown at checkout. Card payments (Visa / Mastercard) are coming soon.",
      },
      {
        q: "How does cash on delivery work?",
        a: "Choose Cash on delivery at checkout. The shops start preparing your order right away, and you pay the rider the order total in cash when it arrives. Please have the exact amount ready.",
      },
      {
        q: "How do I pay by Lipa Namba?",
        a: "Choose Lipa Namba at checkout. On your phone, use your network's Lipa Namba / pay-by-till option to pay the till number shown, for exactly the order total. Then enter the transaction ID from the confirmation SMS and place the order. We confirm the payment by hand, usually within a few hours, and your order ships once it's confirmed.",
      },
      {
        q: "How does mobile-money payment work?",
        a: "At checkout, choose your network and enter your mobile-money number. You'll receive a prompt on your phone — enter your PIN to approve it. Your order updates automatically once the payment is confirmed.",
      },
      {
        q: "I didn't receive the payment prompt. What should I do?",
        a: "Make sure your phone is on, has network coverage, and that the number and network you entered are correct. Then open the order from My Orders and try paying again. If it still doesn't arrive, contact support.",
      },
      {
        q: "Money was deducted but my order says payment failed.",
        a: "Don't pay again. Contact our support team with your order number and the mobile-money transaction reference from your SMS, and we'll confirm the payment and fix your order.",
      },
    ],
  },
  {
    id: "delivery",
    title: "Delivery",
    items: [
      {
        q: "How is the delivery fee calculated?",
        a: "Delivery is priced per shop, based on the distance from each shop to the pin you drop at checkout. If your order includes items from more than one shop, you'll see a separate delivery line for each. The exact fee is always shown before you pay.",
      },
      {
        q: "Where do you deliver?",
        a: "We deliver within a set distance of each shop. If your location is outside a shop's delivery range, checkout will let you know before you pay so you can choose a different address or shop.",
      },
      {
        q: "Who delivers my order?",
        a: "Orders are delivered by MangiMall riders straight to the location you pinned. Make sure the phone number on your order is reachable so the rider can contact you.",
      },
    ],
  },
  {
    id: "returns",
    title: "Returns & refunds",
    items: [
      {
        q: "I received a wrong, damaged or fake item. What do I do?",
        a: "Contact our support team as soon as possible with your order number and photos of the item. We'll review your case with the shop and arrange a return, replacement or refund.",
      },
      {
        q: "How do refunds work?",
        a: "Approved refunds are sent back to the mobile-money number you paid with. Our support team will keep you updated until it's complete.",
      },
      {
        q: "What is Buyer Protection?",
        a: "Every shop on MangiMall is reviewed and approved before it can sell. If something goes wrong with an order, our support team steps in between you and the shop to get it resolved.",
      },
    ],
  },
  {
    id: "account",
    title: "Account & security",
    items: [
      {
        q: "How do I create an account?",
        a: "Click Register, choose a Customer account, and enter your name, email and a password. We'll send you an email to verify your address.",
      },
      {
        q: "I forgot my password.",
        a: 'On the sign-in page, click "Forgot password" and enter your email. We\'ll send you a link to set a new password.',
      },
      {
        q: "How do I update my details?",
        a: "Sign in and open your Account page to update your profile information.",
      },
      {
        q: "Is my payment information safe?",
        a: "Yes. You approve every payment with your own PIN on your phone, and MangiMall never sees or stores your mobile-money PIN.",
      },
    ],
  },
  {
    id: "reviews",
    title: "Reviews",
    items: [
      {
        q: "Can I review a product?",
        a: "Yes — once an item you bought has been delivered, you can leave a rating and review on the product page. You can review each product once.",
      },
      {
        q: "Are reviews genuine?",
        a: "Only customers who bought and received a product can review it, so every review comes from a real purchase.",
      },
    ],
  },
  {
    id: "selling",
    title: "Selling on MangiMall",
    items: [
      {
        q: "How do I open a shop?",
        a: "Click Register, choose a Vendor account and enter your shop name. Already shopping with us? Use the same email and password and the shop will be added to your existing account.",
      },
      {
        q: "How long does shop approval take?",
        a: "New shops start as Pending while our team reviews them. You'll be able to sell once your shop is approved. If a shop isn't approved, we'll share the reason so you can address it.",
      },
      {
        q: "How do I add products and manage orders?",
        a: "From your vendor dashboard, add products with photos, prices and stock. When customers order, you'll see the items under Orders. Move each one to Processing while you prepare it; a MangiMall rider then picks it up and marks it Shipped and Delivered.",
      },
      {
        q: "What does it cost to sell, and how do I get paid?",
        a: "MangiMall takes a commission on each sale, and you can see your rate, sales and balance on your Earnings page. Payouts are sent to your mobile-money account.",
      },
    ],
  },
];

export default function HelpPage() {
  return (
    <PageShell size="md">
      <Card variant="hero" className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold">Help Center &amp; FAQ</h1>
        <p className="text-sm text-text-inverse/70">
          Quick answers about ordering, payments, delivery and selling on MangiMall.
        </p>
      </Card>

      <FaqList sections={FAQ_SECTIONS} />

      <Card variant="hero" className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <h2 className="text-lg font-semibold">Still need help?</h2>
          <p className="text-sm text-text-inverse/70">
            Our support team is available every day, 8am – 10pm EAT. Have your order number ready.
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
