"use client";

import { useState } from "react";
import Link from "next/link";
import { listAdminAuditEvents, type AuditEvent } from "@/lib/api-client";
import { useApi, useRequireRole } from "@/lib/use-api";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Pill, type PillTone } from "@/components/ui/pill";
import { FormField, inputClassName } from "@/components/ui/form-field";
import { EmptyText, ErrorText, LoadingText } from "@/components/ui/status-text";
import { Pager } from "@/components/pager";

/** Action areas, sent to the API as a prefix ("shop." matches every shop action). */
const AREAS: { label: string; prefix: string }[] = [
  { label: "Sign-in & accounts", prefix: "auth." },
  { label: "Customers", prefix: "customer." },
  { label: "Riders", prefix: "rider." },
  { label: "Shops", prefix: "shop." },
  { label: "Categories", prefix: "category." },
  { label: "Products", prefix: "product." },
  { label: "Reviews", prefix: "review." },
  { label: "Orders", prefix: "order." },
  { label: "Order lines", prefix: "order_item." },
  { label: "Payments", prefix: "payment." },
  { label: "Payouts", prefix: "payout." },
  { label: "Payout details", prefix: "payout_details." },
  { label: "Platform settings", prefix: "settings." },
];

const ROLES = ["ADMINISTRATOR", "VENDOR", "CUSTOMER", "RIDER", "SYSTEM"];

const ROLE_TONES: Record<string, PillTone> = {
  ADMINISTRATOR: "approved",
  VENDOR: "processing",
  RIDER: "shipped",
  SYSTEM: "neutral",
};

function actionTone(action: string): PillTone {
  if (/(failed|rejected|blocked|deleted|deactivated|expired)$/.test(action)) return "rejected";
  if (/(approved|confirmed|completed|created|published|placed)$/.test(action)) return "delivered";
  return "neutral";
}

/** Where the target lives in the admin area, when it has its own page. */
function targetHref(event: AuditEvent): string | null {
  const id = event.target_id;
  if (!id) return null;
  switch (event.target_type) {
    case "shop":
      return `/admin/shops/${id}`;
    case "order":
      return `/admin/orders/${id}`;
    case "payout":
      return `/admin/payouts/${id}`;
    case "user":
      return event.action.startsWith("customer.") ? `/admin/customers/${id}` : null;
    default:
      return null;
  }
}

function roleLabel(role: string): string {
  return role.charAt(0) + role.slice(1).toLowerCase();
}

export default function AdminAuditLogPage() {
  const allowed = useRequireRole("ADMINISTRATOR");
  const [filters, setFilters] = useState({
    from: "",
    to: "",
    action: "",
    actor: "",
    actorRole: "",
  });
  const [actorDraft, setActorDraft] = useState("");
  const [page, setPage] = useState(1);
  const events = useApi(
    () => listAdminAuditEvents({ ...filters, page }),
    `${filters.from}|${filters.to}|${filters.action}|${filters.actor}|${filters.actorRole}|${page}`,
    allowed,
  );

  function updateFilters(next: Partial<typeof filters>) {
    setFilters((prev) => ({ ...prev, ...next }));
    setPage(1);
  }

  if (!allowed) {
    return (
      <PageShell size="md" className="min-h-screen items-center justify-center">
        <LoadingText />
      </PageShell>
    );
  }

  return (
    <PageShell
      size="lg"
      title="Audit Log"
      description="Who did what, and when: sign-ins, admin decisions, vendor and rider changes, and payment events."
    >
      <form
        className="flex flex-wrap items-end gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          updateFilters({ actor: actorDraft.trim() });
        }}
      >
        <FormField label="Actor email">
          <input
            type="search"
            placeholder="name@example.com"
            value={actorDraft}
            onChange={(e) => setActorDraft(e.target.value)}
            className={inputClassName}
          />
        </FormField>
        <FormField label="Area">
          <select
            value={filters.action}
            onChange={(e) => updateFilters({ action: e.target.value })}
            className={inputClassName}
          >
            <option value="">Any</option>
            {AREAS.map((area) => (
              <option key={area.prefix} value={area.prefix}>
                {area.label}
              </option>
            ))}
          </select>
        </FormField>
        <FormField label="Role">
          <select
            value={filters.actorRole}
            onChange={(e) => updateFilters({ actorRole: e.target.value })}
            className={inputClassName}
          >
            <option value="">Any</option>
            {ROLES.map((role) => (
              <option key={role} value={role}>
                {roleLabel(role)}
              </option>
            ))}
          </select>
        </FormField>
        <FormField label="From">
          <input
            type="date"
            value={filters.from}
            onChange={(e) => updateFilters({ from: e.target.value })}
            className={inputClassName}
          />
        </FormField>
        <FormField label="To">
          <input
            type="date"
            value={filters.to}
            onChange={(e) => updateFilters({ to: e.target.value })}
            className={inputClassName}
          />
        </FormField>
        <Button type="submit" variant="secondary" size="sm">
          Search
        </Button>
      </form>

      {events.error && <ErrorText>{events.error}</ErrorText>}
      {events.isLoading && !events.data ? (
        <LoadingText>Loading audit log…</LoadingText>
      ) : !events.data || events.data.results.length === 0 ? (
        <EmptyText>No events match.</EmptyText>
      ) : (
        <>
          <p className="text-sm text-text-muted">{events.data.count} events</p>
          <ul className="flex flex-col gap-3">
            {events.data.results.map((event) => (
              <AuditEventRow key={event.id} event={event} />
            ))}
          </ul>
          <Pager
            previous={events.data.previous}
            next={events.data.next}
            onPrevious={() => setPage((p) => p - 1)}
            onNext={() => setPage((p) => p + 1)}
          />
        </>
      )}
    </PageShell>
  );
}

function AuditEventRow({ event }: { event: AuditEvent }) {
  const href = targetHref(event);
  const hasMetadata = Object.keys(event.metadata).length > 0;
  const role = event.actor_role;

  return (
    <Card as="li" padding="sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-medium text-text-primary">
            <Pill tone={actionTone(event.action)}>{event.action_label}</Pill>{" "}
            {event.target_repr &&
              (href ? (
                <Link href={href} className="underline-offset-2 hover:underline">
                  {event.target_repr}
                </Link>
              ) : (
                <span>{event.target_repr}</span>
              ))}
          </p>
          <p className="mt-1 break-all text-sm text-text-muted">
            {event.actor_email || (role === "SYSTEM" ? "System" : "Anonymous")}
            {role && role !== "SYSTEM" && (
              <>
                {" "}
                <Pill tone={ROLE_TONES[role] ?? "neutral"}>{roleLabel(role)}</Pill>
              </>
            )}
            {event.ip_address && <> &middot; {event.ip_address}</>}
          </p>
        </div>
        <p className="text-sm text-text-muted">{new Date(event.created_at).toLocaleString()}</p>
      </div>
      {(hasMetadata || event.user_agent) && (
        <details className="mt-2 text-sm">
          <summary className="cursor-pointer text-text-muted">Details</summary>
          <dl className="mt-2 grid grid-cols-[max-content_1fr] gap-x-3 gap-y-1">
            <dt className="text-text-muted">Action</dt>
            <dd className="break-all font-mono text-xs leading-5">{event.action}</dd>
            {Object.entries(event.metadata).map(([key, value]) => (
              <MetadataEntry key={key} name={key} value={value} />
            ))}
            {event.user_agent && (
              <>
                <dt className="text-text-muted">Device</dt>
                <dd className="break-all text-xs leading-5">{event.user_agent}</dd>
              </>
            )}
          </dl>
        </details>
      )}
    </Card>
  );
}

function MetadataEntry({ name, value }: { name: string; value: unknown }) {
  return (
    <>
      <dt className="text-text-muted">{name.replace(/_/g, " ")}</dt>
      <dd className="break-all font-mono text-xs leading-5">
        {typeof value === "string" ? value : JSON.stringify(value)}
      </dd>
    </>
  );
}
