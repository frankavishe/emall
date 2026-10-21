import { ApiError } from "./api-client";

// Mirrors MAX_AVATAR_SIZE_BYTES in backend/apps/accounts/serializers.py.
export const MAX_AVATAR_SIZE_BYTES = 2 * 1024 * 1024;

// Mirrors PHONE_REGEX in backend/apps/core/validators.py.
const PHONE_PATTERN = /^\+?[0-9]{9,15}$/;

export type ProfileForm = { name: string; phone: string };
export type ProfileErrors = Partial<Record<keyof ProfileForm, string>>;

/** The same rules the server applies to `PATCH /api/auth/me`; empty when the form is valid. */
export function validateProfile(form: ProfileForm): ProfileErrors {
  const errors: ProfileErrors = {};
  const name = form.name.trim();
  if (!name) errors.name = "Enter your full name.";
  else if (name.length < 2) errors.name = "Your name must be at least 2 characters.";
  else if (name.length > 255) errors.name = "Your name must be 255 characters or fewer.";
  const phone = form.phone.trim();
  if (phone && !PHONE_PATTERN.test(phone)) {
    errors.phone = "Enter a valid phone number, e.g. +255712345678.";
  }
  return errors;
}

/** DRF field errors (`{"phone": ["..."]}`) from a failed save, keyed by form field. */
export function profileFieldErrors(err: unknown): ProfileErrors {
  if (!(err instanceof ApiError) || !err.body || typeof err.body !== "object") return {};
  const errors: ProfileErrors = {};
  for (const field of ["name", "phone"] as const) {
    const value = (err.body as Record<string, unknown>)[field];
    const first = Array.isArray(value) ? value[0] : value;
    if (typeof first === "string") errors[field] = first;
  }
  return errors;
}
