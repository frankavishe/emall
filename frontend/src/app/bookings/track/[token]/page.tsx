"use client";

import { useParams } from "next/navigation";
import { cancelGuestBooking, getGuestBooking } from "@/lib/api-client";
import { useApi } from "@/lib/use-api";
import { BookingDetailScreen } from "@/components/booking/booking-detail-screen";

const BACK = { href: "/services", label: "Browse services" };

/** A guest's booking (booked without an account), reached only through its private link. */
export default function GuestBookingPage() {
  const params = useParams<{ token: string }>();
  const booking = useApi(() => getGuestBooking(params.token), params.token, true);

  return (
    <BookingDetailScreen
      booking={booking}
      bookingKey={{ token: params.token }}
      cancel={() => cancelGuestBooking(params.token)}
      back={BACK}
      notice={
        <p className="text-sm text-text-muted">
          Bookmark this page to follow your booking. We also emailed you this private link; anyone
          with it can see and cancel the booking.
        </p>
      }
    />
  );
}
