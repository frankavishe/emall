"use client";

import { useState } from "react";
import { errorMessage, updateMyProfile } from "@/lib/api-client";
import { useAuth, type AuthUser } from "@/lib/auth-context";
import { profileFieldErrors, validateProfile, type ProfileErrors } from "@/lib/profile";
import { Button } from "@/components/ui/button";
import { FormField, inputClassName } from "@/components/ui/form-field";
import { ErrorText } from "@/components/ui/status-text";

/** One label/value row of a profile `<dl>`. */
export function Detail({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5 sm:flex-row sm:justify-between sm:gap-4">
      <dt className="text-text-muted">{label}</dt>
      <dd className="font-medium text-text-primary sm:text-right">{children}</dd>
    </div>
  );
}

/** Name, email and phone: read-only until "Edit profile", then a validated form. Email is shown
 * but never editable — it is the sign-in identity. */
export function PersonalInfoForm({ user }: { user: AuthUser }) {
  const { refreshUser } = useAuth();
  const [isEditing, setIsEditing] = useState(false);
  const [form, setForm] = useState({ name: user.name, phone: user.phone });
  const [errors, setErrors] = useState<ProfileErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  function startEditing() {
    setForm({ name: user.name, phone: user.phone });
    setErrors({});
    setFormError(null);
    setNotice(null);
    setIsEditing(true);
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setFormError(null);
    const found = validateProfile(form);
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    setIsSaving(true);
    try {
      await updateMyProfile({ name: form.name.trim(), phone: form.phone.trim() });
      await refreshUser();
      setIsEditing(false);
      setNotice("Profile saved.");
    } catch (err) {
      const fieldErrors = profileFieldErrors(err);
      setErrors(fieldErrors);
      if (Object.keys(fieldErrors).length === 0) setFormError(errorMessage(err));
    } finally {
      setIsSaving(false);
    }
  }

  if (!isEditing) {
    return (
      <div className="flex flex-col gap-4">
        <dl className="flex flex-col gap-3 text-sm">
          <Detail label="Full name">{user.name}</Detail>
          <Detail label="Email">{user.email}</Detail>
          <Detail label="Phone">{user.phone || "—"}</Detail>
        </dl>
        <div className="flex items-center gap-3">
          <Button variant="secondary" size="sm" onClick={startEditing}>
            Edit profile
          </Button>
          {notice && (
            <p role="status" className="text-sm text-status-delivered">
              {notice}
            </p>
          )}
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
      <FormField label="Full name">
        <input
          className={inputClassName}
          value={form.name}
          onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))}
          maxLength={255}
          autoComplete="name"
          aria-invalid={!!errors.name}
          required
        />
        {errors.name && <ErrorText>{errors.name}</ErrorText>}
      </FormField>
      <FormField label="Email">
        <input className={inputClassName} value={user.email} disabled readOnly />
        <span className="text-xs font-normal text-text-muted">
          Your email is your sign-in. Ask a Super Admin to change it.
        </span>
      </FormField>
      <FormField label="Phone">
        <input
          className={inputClassName}
          type="tel"
          value={form.phone}
          onChange={(event) => setForm((prev) => ({ ...prev, phone: event.target.value }))}
          placeholder="+255712345678"
          autoComplete="tel"
          aria-invalid={!!errors.phone}
        />
        {errors.phone && <ErrorText>{errors.phone}</ErrorText>}
      </FormField>
      {formError && <ErrorText>{formError}</ErrorText>}
      <div className="flex gap-2">
        <Button type="submit" size="sm" disabled={isSaving}>
          {isSaving ? "Saving…" : "Save changes"}
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          disabled={isSaving}
          onClick={() => setIsEditing(false)}
        >
          Cancel
        </Button>
      </div>
    </form>
  );
}
