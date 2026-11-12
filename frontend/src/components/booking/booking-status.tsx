import type { BookingHistoryEvent, BookingStatus, RefundReason } from "@/lib/api-client";
import { formatMarketDateTime } from "@/lib/market-time";
import { Pill, statusToTone } from "@/components/ui/pill";

export const BOOKING_STATUS_LABELS: Record<BookingStatus, string> = {
  REQUESTED: "Requested",
  AWAITING_PAYMENT: "Awaiting payment",
  CONFIRMED: "Confirmed",
  COMPLETED: "Completed",
  NO_SHOW: "No-show",
  DECLINED: "Declined",
  EXPIRED: "Expired",
  CANCELLED: "Cancelled",
};

export const BOOKING_STATUSES = Object.keys(BOOKING_STATUS_LABELS) as BookingStatus[];

/** Why money is owed back, as staff see it (the customer's page words these for the customer). */
export const REFUND_REASON_LABELS: Record<RefundReason, string> = {
  CUSTOMER_CANCELLED: "Customer cancelled",
  PROVIDER_CANCELLED: "Provider cancelled",
  ADMIN_CANCELLED: "Administrator cancelled",
  LATE_PAYMENT: "Paid too late",
};

export function BookingStatusPill({ status }: { status: BookingStatus }) {
  return <Pill tone={statusToTone(status)}>{BOOKING_STATUS_LABELS[status]}</Pill>;
}

/** A booking's status changes, oldest first. */
export function BookingHistory({ events }: { events: BookingHistoryEvent[] }) {
  return (
    <ol className="flex flex-col gap-2">
      {events.map((event, index) => (
        <li key={index} className="text-sm text-text-muted">
          <span className="font-medium text-text-primary">
            {BOOKING_STATUS_LABELS[event.status]}
          </span>{" "}
          &middot; {formatMarketDateTime(event.created_at)}
          {event.actor_email !== undefined && <> &middot; {event.actor_email ?? "System"}</>}
          {event.reason && <span className="block">{event.reason}</span>}
        </li>
      ))}
    </ol>
  );
}
