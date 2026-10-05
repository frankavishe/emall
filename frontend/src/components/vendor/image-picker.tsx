"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { ErrorText } from "@/components/ui/status-text";

// Mirrors MAX_PRODUCT_IMAGE_SIZE_BYTES / MAX_PRODUCT_IMAGES in backend/apps/catalog/serializers.py.
export const MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024;
export const MAX_IMAGES = 10;

export type ExistingImage = { id: number; url: string };

type ImagePickerProps = {
  files: File[];
  onFilesChange: (files: File[]) => void;
  existing?: ExistingImage[];
  removedIds?: number[];
  onRemovedIdsChange?: (ids: number[]) => void;
};

/** Accumulating multi-image picker: each pick appends to the selection (instead of the native
 * input's replace-on-pick behaviour), with thumbnails and per-image remove. On the edit page it
 * also shows the product's existing images, which can be marked for removal. */
export function ImagePicker({
  files,
  onFilesChange,
  existing = [],
  removedIds = [],
  onRemovedIdsChange,
}: ImagePickerProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);

  const previews = useMemo(() => files.map((file) => URL.createObjectURL(file)), [files]);
  useEffect(() => () => previews.forEach((url) => URL.revokeObjectURL(url)), [previews]);

  const keptExistingCount = existing.filter((image) => !removedIds.includes(image.id)).length;
  const remaining = MAX_IMAGES - keptExistingCount - files.length;

  function handlePick(event: React.ChangeEvent<HTMLInputElement>) {
    const picked = Array.from(event.target.files ?? []);
    // Reset so picking the same file again still fires onChange.
    event.target.value = "";
    setError(null);

    const tooBig = picked.filter((file) => file.size > MAX_IMAGE_SIZE_BYTES);
    const accepted = picked.filter((file) => file.size <= MAX_IMAGE_SIZE_BYTES);
    const fitting = accepted.slice(0, Math.max(remaining, 0));

    const problems: string[] = [];
    if (tooBig.length > 0) {
      problems.push(`${tooBig.map((file) => file.name).join(", ")} is over 5MB.`);
    }
    if (fitting.length < accepted.length) {
      problems.push(`A product can have at most ${MAX_IMAGES} images.`);
    }
    if (problems.length > 0) setError(problems.join(" "));

    if (fitting.length > 0) onFilesChange([...files, ...fitting]);
  }

  function toggleExisting(id: number) {
    if (!onRemovedIdsChange) return;
    onRemovedIdsChange(
      removedIds.includes(id)
        ? removedIds.filter((removed) => removed !== id)
        : [...removedIds, id],
    );
  }

  const hasAny = existing.length > 0 || files.length > 0;

  return (
    <div className="flex flex-col gap-2 text-sm font-medium text-text-primary">
      <span>Images</span>
      {hasAny && (
        <ul className="grid grid-cols-3 gap-2 sm:grid-cols-4">
          {existing.map((image) => {
            const isRemoved = removedIds.includes(image.id);
            return (
              <li key={`existing-${image.id}`} className="flex flex-col gap-1">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={image.url}
                  alt=""
                  className={`aspect-square w-full rounded-control border border-border object-cover ${isRemoved ? "opacity-30" : ""}`}
                />
                <Button
                  variant={isRemoved ? "secondary" : "ghost"}
                  size="sm"
                  onClick={() => toggleExisting(image.id)}
                >
                  {isRemoved ? "Undo" : "Remove"}
                </Button>
              </li>
            );
          })}
          {files.map((file, index) => (
            <li key={`new-${index}-${file.name}`} className="flex flex-col gap-1">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={previews[index]}
                alt={file.name}
                className="aspect-square w-full rounded-control border border-border object-cover"
              />
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onFilesChange(files.filter((_, i) => i !== index))}
              >
                Remove
              </Button>
            </li>
          ))}
        </ul>
      )}
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        multiple
        onChange={handlePick}
        className="hidden"
      />
      <div className="flex items-center gap-3">
        <Button
          variant="secondary"
          size="sm"
          disabled={remaining <= 0}
          onClick={() => inputRef.current?.click()}
        >
          {hasAny ? "Add more images" : "Add images"}
        </Button>
        <span className="text-xs font-normal text-text-muted">
          {keptExistingCount + files.length}/{MAX_IMAGES} · up to 5MB each
        </span>
      </div>
      {error && <ErrorText>{error}</ErrorText>}
    </div>
  );
}
