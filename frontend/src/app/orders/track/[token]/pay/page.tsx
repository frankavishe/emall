"use client";

import { useCallback } from "react";
import { useParams } from "next/navigation";
import { getGuestOrder, getGuestPaymentStatus } from "@/lib/api-client";
import { OrderPaymentScreen } from "@/components/order/order-payment-screen";

const BACK = { href: "/products", label: "Continue shopping" };

/** A guest's "check your phone" page (guest checkout). */
export default function GuestOrderPaymentPage() {
  const params = useParams<{ token: string }>();
  const loadOrder = useCallback(() => getGuestOrder(params.token), [params.token]);
  const loadStatus = useCallback(() => getGuestPaymentStatus(params.token), [params.token]);

  return (
    <OrderPaymentScreen
      enabled
      loadOrder={loadOrder}
      loadStatus={loadStatus}
      orderHref={`/orders/track/${params.token}`}
      back={BACK}
    />
  );
}
