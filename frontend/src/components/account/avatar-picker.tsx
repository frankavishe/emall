"use client";

import { useRef, useState } from "react";
import { Avatar } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { ErrorText } from "@/components/ui/status-text";
import { errorMessage, removeMyAvatar, uploadMyAvatar } from "@/lib/api-client";
import { useAuth, type AuthUser } from "@/lib/auth-context";
import { MAX_AVATAR_SIZE_BYTES } from "@/lib/profile";

/** Upload, replace or remove the signed-in user's photo. Saves immediately, then refreshes the
 * profile so the top bar and nav pick up the new photo. */
export function AvatarPicker({ user }: { user: AuthUser }) {
  const { refreshUser } = useAuth();
  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  async function save(action: () => Promise<void>) {
    setError(null);
    setIsSaving(true);
    try {
      await action();
      await refreshUser();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setIsSaving(false);
    }
  }

  function handlePick(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    // Reset so picking the same file again still fires onChange.
    event.target.value = "";
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      setError(`${file.name} is not an image.`);
      return;
    }
    if (file.size > MAX_AVATAR_SIZE_BYTES) {
      setError(`${file.name} is over 2MB.`);
      return;
    }
    void save(() => uploadMyAvatar(file));
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-4">
        <Avatar name={user.name} src={user.avatar_url} size="lg" />
        <div className="flex flex-wrap gap-2">
          <input
            ref={inputRef}
            type="file"
            accept="image/*"
            onChange={handlePick}
            className="hidden"
            data-testid="avatar-input"
          />
          <Button
            variant="secondary"
            size="sm"
            disabled={isSaving}
            onClick={() => inputRef.current?.click()}
          >
            {isSaving ? "Saving…" : user.avatar_url ? "Change photo" : "Upload photo"}
          </Button>
          {user.avatar_url && (
            <Button
              variant="ghost"
              size="sm"
              disabled={isSaving}
              onClick={() => save(removeMyAvatar)}
            >
              Remove
            </Button>
          )}
        </div>
      </div>
      <p className="text-xs text-text-muted">JPG, PNG or WebP, up to 2MB.</p>
      {error && <ErrorText>{error}</ErrorText>}
    </div>
  );
}
