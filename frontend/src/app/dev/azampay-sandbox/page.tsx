"use client";

import { useCallback, useEffect, useState } from "react";
import {
  decideSimulatedPush,
  errorMessage,
  listSimulatedPushes,
  MOBILE_MONEY_PROVIDERS,
  PAYMENT_SIMULATOR_ENABLED,
  type SimulatedPush,
} from "@/lib/api-client";
import { formatCurrency } from "@/lib/currency";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { inputClassName } from "@/components/ui/form-field";
import { EmptyText, ErrorText } from "@/components/ui/status-text";

const REFRESH_MS = 2000;

/** Dev-only stand-in for the customer's phone while AzamPay credentials are pending: lists the
 * USSD pushes the simulator "sent" and approves or rejects them, which makes the backend run its
 * real AzamPay callback handler. Requires PAYMENT_BACKEND=azampay_simulator on the backend and
 * NEXT_PUBLIC_PAYMENT_SIMULATOR=true here. */
export default function AzamPaySandboxPage() {
  const [pushes, setPushes] = useState<SimulatedPush[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [log, setLog] = useState<string[]>([]);

  const refresh = useCallback(async () => {
    try {
      setPushes(await listSimulatedPushes());
      setError(null);
    } catch (err) {
      setError(
        errorMessage(err, "Can't reach the simulator. Is PAYMENT_BACKEND=azampay_simulator set?"),
      );
    }
  }, []);

  useEffect(() => {
    if (!PAYMENT_SIMULATOR_ENABLED) return;
    void refresh();
    const timer = setInterval(() => void refresh(), REFRESH_MS);
    return () => clearInterval(timer);
  }, [refresh]);

  async function decide(push: SimulatedPush, decision: "approve" | "reject", pin?: string) {
    try {
      const result = await decideSimulatedPush(push.reference, decision, pin);
      setLog((prev) => [`Order #${push.order_id}: ${decision} → ${result.outcome}`, ...prev]);
      await refresh();
    } catch (err) {
      setLog((prev) => [`Order #${push.order_id}: ${errorMessage(err)}`, ...prev]);
    }
  }

  if (!PAYMENT_SIMULATOR_ENABLED) {
    return (
      <PageShell size="md" className="min-h-screen items-center justify-center">
        <EmptyText>The AzamPay sandbox simulator is turned off.</EmptyText>
      </PageShell>
    );
  }

  return (
    <PageShell size="md">
      <div>
        <h1 className="text-2xl font-semibold text-text-primary">AzamPay sandbox phone</h1>
        <p className="mt-1 text-sm text-text-muted">
          Development only. Each card is a payment prompt pushed to a customer&apos;s phone. Enter
          any 4-digit PIN to approve it, or reject it. The backend then processes an
          AzamPay-shaped callback exactly as it would from AzamPay.
        </p>
      </div>

      {error && <ErrorText>{error}</ErrorText>}

      {pushes.length === 0 && !error ? (
        <EmptyText>No pending payment prompts. Check out with mobile money to create one.</EmptyText>
      ) : (
        <ul className="flex flex-col gap-4">
          {pushes.map((push) => (
            <PushCard key={push.reference} push={push} onDecide={decide} />
          ))}
        </ul>
      )}

      {log.length > 0 && (
        <Card variant="muted" padding="sm">
          <h2 className="mb-2 text-sm font-semibold text-text-muted">Callbacks sent</h2>
          <ul className="flex flex-col gap-1 font-mono text-xs text-text-primary">
            {log.map((line, index) => (
              <li key={index}>{line}</li>
            ))}
          </ul>
        </Card>
      )}
    </PageShell>
  );
}

function PushCard({
  push,
  onDecide,
}: {
  push: SimulatedPush;
  onDecide: (push: SimulatedPush, decision: "approve" | "reject", pin?: string) => Promise<void>;
}) {
  const [pin, setPin] = useState("");
  const [busy, setBusy] = useState(false);
  const providerLabel =
    MOBILE_MONEY_PROVIDERS.find((option) => option.value === push.provider)?.label ??
    push.provider;

  async function run(decision: "approve" | "reject") {
    setBusy(true);
    await onDecide(push, decision, decision === "approve" ? pin : undefined);
    setBusy(false);
  }

  return (
    <Card as="li" className="flex flex-col gap-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-text-primary">{providerLabel}</p>
          <p className="text-xs text-text-muted">
            To {push.msisdn} · order #{push.order_id}
          </p>
        </div>
        <p className="text-lg font-semibold text-text-primary">{formatCurrency(push.amount)}</p>
      </div>
      <p className="text-sm text-text-muted">
        MangiMall is requesting TZS {push.amount}. Enter your PIN to confirm.
      </p>
      <div className="flex flex-wrap items-center gap-2">
        <input
          type="password"
          inputMode="numeric"
          maxLength={4}
          placeholder="PIN"
          aria-label="PIN"
          value={pin}
          onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))}
          className={`${inputClassName} w-24`}
        />
        <Button size="sm" disabled={busy || pin.length !== 4} onClick={() => run("approve")}>
          Approve
        </Button>
        <Button size="sm" variant="danger" disabled={busy} onClick={() => run("reject")}>
          Reject
        </Button>
      </div>
    </Card>
  );
}
