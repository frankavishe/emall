import type { ReactNode } from "react";
import { NewsletterForm } from "@/components/newsletter-form";

type FooterLink = { label: string; href: string };

const ABOUT_LINKS: FooterLink[] = [
  { label: "About Us", href: "#" },
  { label: "Our Merchants", href: "#" },
  { label: "Careers & Internships", href: "#" },
  { label: "Press & Media", href: "#" },
  { label: "Sustainability Impact", href: "#" },
];

const CARE_LINKS: FooterLink[] = [
  { label: "Help Center & FAQ", href: "#" },
  { label: "Track Your Order", href: "#" },
  { label: "Returns & Refunds", href: "#" },
  { label: "Delivery Rates", href: "#" },
  { label: "Buyer Protection", href: "#" },
];

const LEGAL_LINKS: FooterLink[] = [
  { label: "Privacy Policy", href: "#" },
  { label: "Terms of Service", href: "#" },
  { label: "Security", href: "#" },
];

const PAYMENT_BADGES = [
  { label: "M-Pesa", className: "text-amber-400" },
  { label: "Tigo Pesa", className: "text-blue-400" },
  { label: "Airtel Money", className: "text-red-400" },
  { label: "Visa / Mastercard", className: "text-slate-200" },
];

/** 24x24 viewBox paths; filled with currentColor. */
const ICONS = {
  location:
    "M12 2a7 7 0 0 0-7 7c0 5.25 7 13 7 13s7-7.75 7-13a7 7 0 0 0-7-7Zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5Z",
  phone:
    "M6.6 10.8a15.1 15.1 0 0 0 6.6 6.6l2.2-2.2a1 1 0 0 1 1-.25 11.4 11.4 0 0 0 3.6.57 1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1c0 1.25.2 2.45.57 3.57a1 1 0 0 1-.25 1L6.6 10.8Z",
  mail: "M4 4h16a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Zm0 2v.5l8 5 8-5V6H4Zm16 2.85-7.47 4.67a1 1 0 0 1-1.06 0L4 8.85V18h16V8.85Z",
  instagram:
    "M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10Zm0 8.2a3.2 3.2 0 1 1 0-6.4 3.2 3.2 0 0 1 0 6.4ZM17.3 5.5a1.2 1.2 0 1 0 0 2.4 1.2 1.2 0 0 0 0-2.4ZM12 3.8c2.67 0 2.99.01 4.04.06 2.71.12 3.98 1.41 4.1 4.1.05 1.05.06 1.37.06 4.04s-.01 2.99-.06 4.04c-.12 2.69-1.38 3.98-4.1 4.1-1.05.05-1.37.06-4.04.06s-2.99-.01-4.04-.06c-2.72-.12-3.98-1.41-4.1-4.1C3.81 14.99 3.8 14.67 3.8 12s.01-2.99.06-4.04c.12-2.69 1.38-3.98 4.1-4.1C9.01 3.81 9.33 3.8 12 3.8ZM12 2c-2.72 0-3.06.01-4.12.06-3.63.17-5.65 2.18-5.82 5.82C2.01 8.94 2 9.28 2 12s.01 3.06.06 4.12c.17 3.63 2.18 5.65 5.82 5.82 1.06.05 1.4.06 4.12.06s3.06-.01 4.12-.06c3.62-.17 5.66-2.18 5.82-5.82.05-1.06.06-1.4.06-4.12s-.01-3.06-.06-4.12c-.16-3.62-2.18-5.65-5.82-5.82C15.06 2.01 14.72 2 12 2Z",
  x: "M17.75 3h3.07l-6.71 7.67L22 21h-6.18l-4.84-6.33L5.44 21H2.37l7.18-8.2L2 3h6.34l4.37 5.78L17.75 3Zm-1.08 16.18h1.7L7.4 4.73H5.58l11.09 14.45Z",
  facebook:
    "M13.5 21v-8h2.7l.4-3.1h-3.1V7.9c0-.9.25-1.5 1.55-1.5h1.65V3.6A22 22 0 0 0 14.3 3.5c-2.4 0-4.05 1.47-4.05 4.16V9.9H7.5V13h2.75v8h3.25Z",
  linkedin:
    "M6.94 8.5H3.56V20h3.38V8.5ZM5.25 3a1.96 1.96 0 1 0 0 3.92 1.96 1.96 0 0 0 0-3.92ZM20.44 13.4c0-3.1-.67-5.15-4.27-5.15-1.73 0-2.89.95-3.36 1.85h-.05V8.5H9.52V20h3.37v-5.7c0-1.5.28-2.95 2.14-2.95 1.83 0 1.86 1.72 1.86 3.05V20h3.37l.18-6.6Z",
  whatsapp:
    "M12.04 2a9.9 9.9 0 0 0-8.5 14.98L2 22l5.17-1.5A9.9 9.9 0 1 0 12.04 2Zm0 18.1a8.2 8.2 0 0 1-4.2-1.15l-.3-.18-3.07.89.9-2.99-.2-.31a8.2 8.2 0 1 1 6.87 3.74Zm4.5-6.14c-.25-.12-1.46-.72-1.69-.8-.23-.08-.39-.12-.55.12-.16.25-.63.8-.78.97-.14.16-.29.18-.53.06-.25-.12-1.04-.38-1.98-1.22a7.4 7.4 0 0 1-1.37-1.7c-.14-.25-.02-.38.11-.5.11-.11.25-.29.37-.43.12-.14.16-.25.25-.41.08-.16.04-.31-.02-.43-.06-.12-.55-1.33-.76-1.82-.2-.48-.4-.41-.55-.42h-.47a.9.9 0 0 0-.65.31c-.23.25-.86.84-.86 2.05s.88 2.38 1 2.54c.12.16 1.73 2.64 4.2 3.7.59.25 1.05.4 1.4.52.59.19 1.13.16 1.55.1.47-.07 1.46-.6 1.67-1.18.2-.58.2-1.07.14-1.18-.06-.1-.22-.16-.47-.28Z",
} as const;

type IconName = keyof typeof ICONS;

function Icon({ name, className }: { name: IconName; className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className} aria-hidden>
      <path d={ICONS[name]} />
    </svg>
  );
}

const SOCIALS: { label: string; icon: IconName; href: string }[] = [
  { label: "Instagram", icon: "instagram", href: "#" },
  { label: "X (Twitter)", icon: "x", href: "#" },
  { label: "Facebook", icon: "facebook", href: "#" },
  { label: "LinkedIn", icon: "linkedin", href: "#" },
  { label: "WhatsApp", icon: "whatsapp", href: "#" },
];

function ContactLine({ icon, children }: { icon: IconName; children: ReactNode }) {
  return (
    <p className="flex items-start gap-2">
      <Icon name={icon} className="mt-0.5 h-3.5 w-3.5 shrink-0 text-teal-400" />
      <span>{children}</span>
    </p>
  );
}

function LinkColumn({ title, links }: { title: string; links: FooterLink[] }) {
  return (
    <div className="flex flex-col gap-3">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-white">{title}</h3>
      <ul className="flex flex-col gap-2 text-sm">
        {links.map((link) => (
          <li key={link.label}>
            <a href={link.href} className="transition-colors hover:text-teal-400">
              {link.label}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function Footer() {
  return (
    <footer className="mt-auto bg-navy-900 pb-8 pt-16 text-slate-300">
      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <div className="grid grid-cols-1 gap-10 border-b border-white/10 pb-12 md:grid-cols-2 lg:grid-cols-5">
          <div className="flex flex-col gap-4 lg:col-span-2">
            <div className="flex items-center gap-2">
              <span aria-hidden className="h-2.5 w-2.5 rounded-sm bg-teal-400" />
              <span className="text-2xl font-extrabold tracking-tight text-white">E-Mall</span>
            </div>
            <p className="max-w-sm text-sm leading-relaxed text-slate-400">
              Tanzania&apos;s premier electronics and hardware marketplace. We bridge quality tech
              with verified local dealers like Frank Electronics to guarantee genuine gadgets, fast
              doorstep fulfillment, and dependable warranties.
            </p>
            <div className="flex flex-col gap-1.5 pt-2 text-xs text-slate-400">
              <ContactLine icon="location">
                Mlimani City Mall &amp; Kariakoo, Dar es Salaam, Tanzania
              </ContactLine>
              <ContactLine icon="phone">+255 (0) 744 123 456 / +255 22 210 9988</ContactLine>
              <ContactLine icon="mail">support@emall.co.tz</ContactLine>
            </div>
          </div>

          <LinkColumn title="About" links={ABOUT_LINKS} />
          <LinkColumn title="Customer Care" links={CARE_LINKS} />

          <div className="flex flex-col gap-4">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-white">
              Stay Connected
            </h3>
            <p className="text-xs text-slate-400">
              Subscribe for early alerts on flash tech sales and discount vouchers.
            </p>
            <NewsletterForm />
            <div className="pt-2">
              <span className="mb-2 block text-xs font-medium text-slate-400">
                Follow our socials:
              </span>
              <div className="flex flex-wrap items-center gap-2 text-slate-400">
                {SOCIALS.map((social) => (
                  <a
                    key={social.label}
                    href={social.href}
                    aria-label={social.label}
                    className="flex h-7 w-7 items-center justify-center rounded-full bg-white/10 transition-colors hover:bg-teal-400 hover:text-navy-900"
                  >
                    <Icon name={social.icon} className="h-3.5 w-3.5" />
                  </a>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="flex flex-col items-center justify-between gap-4 pt-8 text-xs text-slate-500 md:flex-row">
          <p>© 2026 E-Mall Technologies Limited. All rights reserved.</p>
          <div className="flex flex-wrap items-center justify-center gap-3">
            <span className="text-[11px] font-medium text-slate-500">Accepted Payments:</span>
            {PAYMENT_BADGES.map((badge) => (
              <span
                key={badge.label}
                className={`rounded bg-white/10 px-2.5 py-1 text-[11px] font-semibold ${badge.className}`}
              >
                {badge.label}
              </span>
            ))}
          </div>
          <div className="flex gap-4">
            {LEGAL_LINKS.map((link) => (
              <a key={link.label} href={link.href} className="hover:underline">
                {link.label}
              </a>
            ))}
          </div>
        </div>
      </div>
    </footer>
  );
}
