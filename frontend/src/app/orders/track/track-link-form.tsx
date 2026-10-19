"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { FormField, inputClassName } from "@/components/ui/form-field";
import { ErrorText } from "@/components/ui/status-text";

const TOKEN_PATTERN = /^[A-Za-z0-9_-]{16,64}$/;
const TRACK_PATH = "/orders/track/";

/** Pulls a guest order's access token out of a pasted tracking link, or a bare token. */
export function extractTrackToken(input: string): string | null {
  const value = input.trim();
  const at = value.indexOf(TRACK_PATH);
  const candidate = at === -1 ? value : value.slice(at + TRACK_PATH.length).split(/[/?#]/)[0];
  return TOKEN_PATTERN.test(candidate) ? candidate : null;
}

/** Takes a guest back to their order from the private link we emailed them. */
export function TrackLinkForm() {
  const router = useRouter();
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const token = extractTrackToken(value);
    if (!token) {
      setError(
        "That doesn't look like a tracking link. Copy the full link from your order confirmation email.",
      );
      return;
    }
    setError(null);
    router.push(`${TRACK_PATH}${token}`);
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3" noValidate>
      <FormField label="Tracking link or code">
        <input
          type="text"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder="https://mangimall.com/orders/track/…"
          autoComplete="off"
          spellCheck={false}
          className={inputClassName}
        />
      </FormField>
      {error && <ErrorText>{error}</ErrorText>}
      <Button type="submit" className="self-start">
        Track order
      </Button>
    </form>
  );
}
