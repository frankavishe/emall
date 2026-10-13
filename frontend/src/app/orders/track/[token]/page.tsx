"use client";

import { useCallback } from "react";
import { useParams } from "next/navigation";
import { getGuestOrder } from "@/lib/api-client";
import { OrderDetailScreen } from "@/components/order/order-detail-screen";

const BACK = { href: "/products", label: "Continue shopping" };

/** A guest's order (guest checkout), reached only through its private link. */
export default function GuestOrderPage() {
  const params = useParams<{ token: string }>();
  const load = useCallback(() => getGuestOrder(params.token), [params.token]);

  return (
    <OrderDetailScreen
      enabled
      load={load}
      orderHref={`/orders/track/${params.token}`}
      back={BACK}
      notice={
        <p className="text-sm text-text-muted">
          Bookmark this page to follow your order. We also emailed you this private link; anyone
          with it can see the order.
        </p>
      }
    />
  );
}
