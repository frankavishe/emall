"use client";

import {
  MOBILE_MONEY_PROVIDERS,
  type MobileMoneyProvider,
  type PaymentMethodOption,
} from "@/lib/api-client";
import { formatCurrency } from "@/lib/currency";
import { FormField, inputClassName } from "@/components/ui/form-field";

// Tanzanian mobile number: 07XXXXXXXX / 06XXXXXXXX, optionally as +255 / 255. The server
// normalises and re-validates it.
const TZ_MOBILE = /^(?:\+?255|0)?[67]\d{8}$/;

export function isValidMobile(value: string): boolean {
  return TZ_MOBILE.test(value.replace(/[\s-]/g, ""));
}

/** What the extra fields of a Lipa Namba or mobile-money payment hold. */
export type PaymentFieldValues = {
  payerReference: string;
  provider: MobileMoneyProvider;
  msisdn: string;
};

export type PaymentFieldErrors = {
  payerReference?: string | null;
  msisdn?: string | null;
};

type Props = {
  /** The selected method; other methods render nothing here. */
  method: string;
  /** The Lipa Namba option, for its till number. */
  lipaNamba?: PaymentMethodOption;
  /** What the customer must pay, when known. */
  amount?: string | null;
  values: PaymentFieldValues;
  errors: PaymentFieldErrors;
  onChange: (values: PaymentFieldValues) => void;
  onErrorsChange: (errors: PaymentFieldErrors) => void;
  /** What is being paid for, used in the instructions. */
  subject?: "order" | "booking";
};

/** The Lipa Namba and mobile-money fields shared by checkout and booking payment. */
export function PaymentMethodFields({
  method,
  lipaNamba,
  amount,
  values,
  errors,
  onChange,
  onErrorsChange,
  subject = "order",
}: Props) {
  const update = (patch: Partial<PaymentFieldValues>) => onChange({ ...values, ...patch });

  if (method === "lipa_namba" && lipaNamba) {
    return (
      <div className="flex flex-col gap-4 rounded-control border border-border bg-card-muted p-4">
        <ol className="list-decimal space-y-1 pl-5 text-sm text-text-muted">
          <li>
            On your phone choose <strong>Lipa kwa Simu</strong> (or your network&apos;s &ldquo;Lipa
            Namba&rdquo; / &ldquo;Pay by till&rdquo; option).
          </li>
          <li>
            Pay till number{" "}
            <strong className="font-mono text-text-primary">{lipaNamba.till_number}</strong>
            {lipaNamba.till_name ? ` (${lipaNamba.till_name})` : ""}
            {amount ? (
              <>
                {" "}
                exactly <strong className="text-text-primary">{formatCurrency(amount)}</strong>
              </>
            ) : null}
            .
          </li>
          <li>Enter the transaction ID from the confirmation SMS below.</li>
        </ol>
        <FormField label="Transaction ID">
          <input
            type="text"
            autoComplete="off"
            autoCapitalize="characters"
            placeholder="e.g. QJK7H2LM9P"
            maxLength={64}
            value={values.payerReference}
            onChange={(e) => {
              update({ payerReference: e.target.value });
              onErrorsChange({ ...errors, payerReference: null });
            }}
            className={inputClassName}
          />
          {errors.payerReference && (
            <span className="text-xs text-status-cancelled">{errors.payerReference}</span>
          )}
        </FormField>
        <p className="text-xs text-text-muted">
          {subject === "order"
            ? "We confirm your payment by hand, usually within a few hours. Your order ships once it's confirmed."
            : "We confirm your payment by hand, usually within a few hours. Your time stays held until then."}
        </p>
      </div>
    );
  }

  if (method === "mobile_money") {
    return (
      <div className="flex flex-col gap-4 rounded-control border border-border bg-card-muted p-4">
        <p className="text-sm text-text-muted">
          We&apos;ll send a payment prompt to this phone. Enter your mobile money PIN there to
          confirm the {subject}.
        </p>
        <FormField label="Network">
          <select
            value={values.provider}
            onChange={(e) => update({ provider: e.target.value as MobileMoneyProvider })}
            className={inputClassName}
          >
            {MOBILE_MONEY_PROVIDERS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </FormField>
        <FormField label="Mobile money number">
          <input
            type="tel"
            inputMode="tel"
            autoComplete="tel"
            placeholder="0712 345 678"
            value={values.msisdn}
            onChange={(e) => {
              update({ msisdn: e.target.value });
              onErrorsChange({ ...errors, msisdn: null });
            }}
            onBlur={() => {
              if (values.msisdn && !isValidMobile(values.msisdn)) {
                onErrorsChange({
                  ...errors,
                  msisdn: "That doesn't look like a Tanzanian mobile number.",
                });
              }
            }}
            className={inputClassName}
          />
          {errors.msisdn && <span className="text-xs text-status-cancelled">{errors.msisdn}</span>}
        </FormField>
      </div>
    );
  }

  return null;
}
