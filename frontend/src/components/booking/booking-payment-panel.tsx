"use client";

import { useEffect, useState } from "react";
import {
  errorMessage,
  getBookingPaymentMethods,
  getBookingPaymentStatus,
  payBooking,
  type BookingDetail,
  type BookingKey,
  type BookingPayRequest,
  type PaymentMethodOption,
} from "@/lib/api-client";
import { formatCurrency } from "@/lib/currency";
import { formatMarketDateTime } from "@/lib/market-time";
import { useRealtimeConnected } from "@/lib/realtime";
import { Button } from "@/components/ui/button";
import { FormField, inputClassName } from "@/components/ui/form-field";
import { ErrorText, LoadingText } from "@/components/ui/status-text";
import {
  isValidMobile,
  PaymentMethodFields,
  type PaymentFieldErrors,
  type PaymentFieldValues,
} from "@/components/payment/payment-method-fields";

// How often to check a pending push when no live update arrives (a guest has no socket).
const POLL_MS = 4000;
const POLL_MS_CONNECTED = 15000;

/** Paying for an accepted booking, and what happens while a payment is being processed. The
 * page reloads the booking (`onChanged`) when the payment settles. */
export function BookingPaymentPanel({
  bookingKey,
  booking,
  onChanged,
}: {
  bookingKey: BookingKey;
  booking: BookingDetail;
  onChanged: () => void;
}) {
  const payment = booking.payment;
  const isPending = payment?.status === "PENDING";
  const canPay = booking.status === "AWAITING_PAYMENT" && !isPending;
  const keyId = "token" in bookingKey ? bookingKey.token : String(bookingKey.id);

  const [methods, setMethods] = useState<PaymentMethodOption[] | null>(null);
  const [methodsError, setMethodsError] = useState<string | null>(null);
  const [method, setMethod] = useState("");
  const [values, setValues] = useState<PaymentFieldValues>({
    payerReference: "",
    provider: "Mpesa",
    msisdn: "",
  });
  const [fieldErrors, setFieldErrors] = useState<PaymentFieldErrors>({});
  const [error, setError] = useState<string | null>(null);
  const [isPaying, setIsPaying] = useState(false);
  const connected = useRealtimeConnected();

  useEffect(() => {
    if (!canPay) return;
    let cancelled = false;
    (async () => {
      try {
        const options = await getBookingPaymentMethods(bookingKey);
        if (cancelled) return;
        setMethods(options);
        setMethodsError(null);
        setMethod((current) =>
          options.some((option) => option.method === current)
            ? current
            : (options[0]?.method ?? ""),
        );
      } catch (err) {
        if (!cancelled) setMethodsError(errorMessage(err));
      }
    })();
    return () => {
      cancelled = true;
    };
    // `bookingKey` is a fresh object each render; `keyId` identifies it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canPay, keyId]);

  // While a push waits on the customer's phone, check on it until it settles.
  useEffect(() => {
    if (!isPending) return;
    const timer = setInterval(
      async () => {
        try {
          const status = await getBookingPaymentStatus(bookingKey);
          if (status.payment_status !== "PENDING" || status.booking_status !== booking.status) {
            onChanged();
          }
        } catch {
          // The next tick tries again.
        }
      },
      connected ? POLL_MS_CONNECTED : POLL_MS,
    );
    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isPending, keyId, connected, booking.status, onChanged]);

  async function handlePay(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    let request: BookingPayRequest;
    if (method === "mobile_money") {
      if (!isValidMobile(values.msisdn)) {
        setFieldErrors({ msisdn: "Enter a Tanzanian mobile number, e.g. 0712345678." });
        return;
      }
      request = {
        payment_method: "mobile_money",
        provider: values.provider,
        msisdn: values.msisdn,
      };
    } else if (method === "lipa_namba") {
      if (!values.payerReference.trim()) {
        setFieldErrors({ payerReference: "Enter the transaction ID from your payment SMS." });
        return;
      }
      request = { payment_method: "lipa_namba", payer_reference: values.payerReference.trim() };
    } else {
      return;
    }
    setIsPaying(true);
    try {
      await payBooking(bookingKey, request);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setIsPaying(false);
      onChanged();
    }
  }

  if (booking.status !== "AWAITING_PAYMENT") return null;

  if (isPending) {
    return (
      <section
        aria-label="Payment"
        className="flex flex-col gap-2 rounded-control border border-border bg-card-muted p-4"
      >
        <h2 className="text-sm font-semibold text-text-primary">Payment in progress</h2>
        <p className="text-sm text-text-muted">
          {payment.method === "lipa_namba"
            ? `We're checking your Lipa Namba payment (transaction ID ${payment.payer_reference}). Your time stays held until we confirm it, usually within a few hours.`
            : `We sent a payment prompt for ${formatCurrency(payment.amount)} to ${payment.msisdn}. Enter your mobile money PIN on your phone to confirm the booking.`}
        </p>
        {payment.method !== "lipa_namba" && <LoadingText>Waiting for your phone…</LoadingText>}
      </section>
    );
  }

  const lipaNamba = methods?.find((option) => option.method === "lipa_namba");

  return (
    <section
      aria-label="Payment"
      className="flex flex-col gap-3 rounded-control border border-border bg-card-muted p-4"
    >
      <h2 className="text-sm font-semibold text-text-primary">
        Pay {formatCurrency(booking.price)} to confirm
      </h2>
      {booking.pay_by && (
        <p className="text-sm text-text-muted">
          Pay by {formatMarketDateTime(booking.pay_by)}, or the booking expires and the time is
          released.
        </p>
      )}
      {payment?.status === "FAILED" && (
        <ErrorText>
          Your last payment didn&apos;t go through
          {payment.failure_reason ? `: ${payment.failure_reason}` : "."} You can try again.
        </ErrorText>
      )}

      {methodsError ? (
        <ErrorText>{methodsError}</ErrorText>
      ) : methods === null ? (
        <LoadingText>Loading payment methods…</LoadingText>
      ) : methods.length === 0 ? (
        <ErrorText>Payments are unavailable right now. Please try again later.</ErrorText>
      ) : (
        <form onSubmit={handlePay} className="flex flex-col gap-3">
          <FormField label="Payment method">
            <select
              value={method}
              onChange={(e) => {
                setMethod(e.target.value);
                setFieldErrors({});
              }}
              className={inputClassName}
            >
              {methods.map((option) => (
                <option key={option.method} value={option.method}>
                  {option.label}
                </option>
              ))}
            </select>
          </FormField>
          <PaymentMethodFields
            method={method}
            lipaNamba={lipaNamba}
            amount={booking.price}
            values={values}
            errors={fieldErrors}
            onChange={setValues}
            onErrorsChange={setFieldErrors}
            subject="booking"
          />
          {error && <ErrorText>{error}</ErrorText>}
          <Button type="submit" disabled={isPaying || !method} className="self-start">
            {isPaying ? "Starting payment…" : `Pay ${formatCurrency(booking.price)}`}
          </Button>
        </form>
      )}
    </section>
  );
}
