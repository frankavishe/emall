"use client";

import { useCallback, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { hasRole, useAuth } from "@/lib/auth-context";
import { getOrder } from "@/lib/api-client";
import { OrderDetailScreen } from "@/components/order/order-detail-screen";

const BACK = { href: "/orders", label: "Back to orders" };

export default function OrderDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { user, isLoading } = useAuth();
  const isCustomer = !isLoading && hasRole(user, "CUSTOMER");

  useEffect(() => {
    if (!isLoading && (!user || !hasRole(user, "CUSTOMER"))) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  const load = useCallback(() => getOrder(params.id), [params.id]);

  return (
    <OrderDetailScreen
      enabled={isCustomer}
      load={load}
      orderHref={`/orders/${params.id}`}
      back={BACK}
    />
  );
}
