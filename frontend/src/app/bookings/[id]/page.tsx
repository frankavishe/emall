"use client";

import { useParams } from "next/navigation";
import { cancelBooking, getBooking } from "@/lib/api-client";
import { useLiveRefresh } from "@/lib/realtime";
import { useApi, useRequireRole } from "@/lib/use-api";
import { BookingDetailScreen } from "@/components/booking/booking-detail-screen";

const BACK = { href: "/bookings", label: "My bookings" };

export default function BookingDetailPage() {
  const params = useParams<{ id: string }>();
  const allowed = useRequireRole("CUSTOMER");
  const { version } = useLiveRefresh(["booking.updated"], { enabled: allowed });
  const booking = useApi(() => getBooking(params.id), `${params.id}|${version}`, allowed);

  return (
    <BookingDetailScreen
      booking={booking}
      ready={allowed}
      cancel={() => cancelBooking(params.id)}
      back={BACK}
    />
  );
}
