"use client";

import { useState } from "react";
import { errorMessage, updateCustomer, type AdminCustomer } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { ErrorText } from "@/components/ui/status-text";

/** Block/Unblock with an inline confirmation for blocking, which logs the customer out. */
export function BlockToggle({
  customer,
  onChanged,
}: {
  customer: Pick<AdminCustomer, "id" | "name" | "is_active">;
  onChanged: (message: string) => void;
}) {
  const [isConfirming, setIsConfirming] = useState(false);
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function apply(isActive: boolean) {
    setIsPending(true);
    setError(null);
    try {
      await updateCustomer(customer.id, { is_active: isActive });
      setIsConfirming(false);
      onChanged(
        isActive
          ? `${customer.name} is unblocked and can log in again.`
          : `${customer.name} is blocked and has been logged out.`,
      );
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setIsPending(false);
    }
  }

  if (!customer.is_active) {
    return (
      <div className="flex flex-col items-end gap-1">
        <Button variant="secondary" size="sm" disabled={isPending} onClick={() => apply(true)}>
          {isPending ? "Unblocking…" : "Unblock"}
        </Button>
        {error && <ErrorText>{error}</ErrorText>}
      </div>
    );
  }

  if (!isConfirming) {
    return (
      <Button variant="danger" size="sm" onClick={() => setIsConfirming(true)}>
        Block
      </Button>
    );
  }

  return (
    <div className="flex flex-col items-end gap-2">
      <p className="text-sm text-text-muted">Block {customer.name}? They&rsquo;ll be logged out.</p>
      <div className="flex gap-2">
        <Button
          variant="ghost"
          size="sm"
          disabled={isPending}
          onClick={() => setIsConfirming(false)}
        >
          Cancel
        </Button>
        <Button variant="danger" size="sm" disabled={isPending} onClick={() => apply(false)}>
          {isPending ? "Blocking…" : "Block"}
        </Button>
      </div>
      {error && <ErrorText>{error}</ErrorText>}
    </div>
  );
}
