"use client";

import { useCallback, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { hasRole, useAuth } from "@/lib/auth-context";
import { getOrder, getPaymentStatus } from "@/lib/api-client";
import { OrderPaymentScreen } from "@/components/order/order-payment-screen";

const BACK = { href: "/orders", label: "Back to orders" };

export default function OrderPaymentPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { user, isLoading } = useAuth();
  const isCustomer = !isLoading && hasRole(user, "CUSTOMER");

  useEffect(() => {
    if (!isLoading && (!user || !hasRole(user, "CUSTOMER"))) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  const loadOrder = useCallback(() => getOrder(params.id), [params.id]);
  const loadStatus = useCallback(() => getPaymentStatus(params.id), [params.id]);

  return (
    <OrderPaymentScreen
      enabled={isCustomer}
      loadOrder={loadOrder}
      loadStatus={loadStatus}
      orderHref={`/orders/${params.id}`}
      back={BACK}
    />
  );
}
