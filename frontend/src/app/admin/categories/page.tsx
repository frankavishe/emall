"use client";

import { useState } from "react";
import {
  createCategory,
  deleteCategory,
  errorMessage,
  listAdminCategories,
  updateCategory,
  type AdminCategory,
} from "@/lib/api-client";
import { useApi, useRequireRole } from "@/lib/use-api";
import { PageShell } from "@/components/ui/page-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Pill } from "@/components/ui/pill";
import { ErrorText, LoadingText, EmptyText } from "@/components/ui/status-text";
import { FormField, inputClassName } from "@/components/ui/form-field";

function productLabel(count: number): string {
  return `${count} ${count === 1 ? "product" : "products"}`;
}

function NewCategoryForm({
  topLevel,
  parentId,
  onCreated,
  onCancel,
}: {
  topLevel: AdminCategory[];
  /** Fixes the parent (the inline "Add subcategory" form); omit to show a parent picker. */
  parentId?: number;
  onCreated: (category: AdminCategory) => void;
  onCancel?: () => void;
}) {
  const [name, setName] = useState("");
  const [parent, setParent] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      const category = await createCategory({
        name,
        parent: parentId ?? (parent ? Number(parent) : null),
      });
      setName("");
      onCreated(category);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-0 flex-1">
          <FormField label={parentId ? "Subcategory name" : "Name"}>
            <input
              required
              maxLength={100}
              value={name}
              onChange={(e) => setName(e.target.value)}
              className={inputClassName}
            />
          </FormField>
        </div>
        {parentId === undefined && (
          <div className="min-w-0 flex-1">
            <FormField label="Parent">
              <select
                value={parent}
                onChange={(e) => setParent(e.target.value)}
                className={inputClassName}
              >
                <option value="">None (top-level)</option>
                {topLevel.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </FormField>
          </div>
        )}
        <div className="flex gap-2">
          {onCancel && (
            <Button type="button" variant="ghost" onClick={onCancel}>
              Cancel
            </Button>
          )}
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Adding…" : "Add"}
          </Button>
        </div>
      </div>
      {error && <ErrorText>{error}</ErrorText>}
    </form>
  );
}

function CategoryRow({
  category,
  onChanged,
  actions,
}: {
  category: AdminCategory;
  onChanged: () => void;
  actions?: React.ReactNode;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [name, setName] = useState(category.name);
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(action: () => Promise<unknown>) {
    setIsPending(true);
    setError(null);
    try {
      await action();
      setIsEditing(false);
      onChanged();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setIsPending(false);
    }
  }

  const deleteHint = category.can_delete
    ? undefined
    : category.children.length > 0
      ? "Delete or move its subcategories first"
      : "Products are listed under this category";

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center justify-between gap-3">
        {isEditing ? (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void run(() => updateCategory(category.id, { name }));
            }}
            className="flex min-w-0 flex-1 flex-wrap items-center gap-2"
          >
            <input
              required
              autoFocus
              maxLength={100}
              value={name}
              onChange={(e) => setName(e.target.value)}
              aria-label="Category name"
              className={`${inputClassName} min-w-0 flex-1`}
            />
            <Button type="submit" size="sm" disabled={isPending}>
              Save
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => {
                setName(category.name);
                setIsEditing(false);
              }}
            >
              Cancel
            </Button>
          </form>
        ) : (
          <div className="min-w-0">
            <p className="font-medium text-text-primary">{category.name}</p>
            <p className="text-sm text-text-muted">
              {category.slug} &middot; {productLabel(category.product_count)}
            </p>
          </div>
        )}
        {!isEditing && (
          <div className="flex flex-wrap gap-2">
            {actions}
            <Button variant="secondary" size="sm" onClick={() => setIsEditing(true)}>
              Rename
            </Button>
            <Button
              variant="danger"
              size="sm"
              disabled={!category.can_delete || isPending}
              title={deleteHint}
              onClick={() => run(() => deleteCategory(category.id))}
            >
              Delete
            </Button>
          </div>
        )}
      </div>
      {error && <ErrorText>{error}</ErrorText>}
    </div>
  );
}

function TopLevelCard({
  category,
  topLevel,
  onChanged,
}: {
  category: AdminCategory;
  topLevel: AdminCategory[];
  onChanged: () => void;
}) {
  const [isAdding, setIsAdding] = useState(false);
  const hasDirectProducts = category.children.length === 0 && category.product_count > 0;

  return (
    <Card as="li" padding="sm" className="flex flex-col gap-3">
      <CategoryRow
        category={category}
        onChanged={onChanged}
        actions={
          <Button
            variant="secondary"
            size="sm"
            disabled={hasDirectProducts}
            title={
              hasDirectProducts
                ? "Products are listed directly under this category. Move them before adding subcategories."
                : undefined
            }
            onClick={() => setIsAdding(true)}
          >
            Add subcategory
          </Button>
        }
      />

      {category.children.length > 0 && (
        <ul className="ml-4 flex flex-col gap-3 border-l border-border pl-4">
          {category.children.map((child) => (
            <li key={child.id}>
              <CategoryRow category={child} onChanged={onChanged} />
            </li>
          ))}
        </ul>
      )}

      {isAdding && (
        <div className="ml-4 border-l border-border pl-4">
          <NewCategoryForm
            topLevel={topLevel}
            parentId={category.id}
            onCreated={() => {
              setIsAdding(false);
              onChanged();
            }}
            onCancel={() => setIsAdding(false)}
          />
        </div>
      )}
    </Card>
  );
}

export default function AdminCategoriesPage() {
  const allowed = useRequireRole("ADMINISTRATOR");
  const categories = useApi(() => listAdminCategories(), "categories", allowed);
  const [notice, setNotice] = useState<string | null>(null);

  if (!allowed) {
    return (
      <PageShell size="md" className="min-h-screen items-center justify-center">
        <LoadingText />
      </PageShell>
    );
  }

  const topLevel = categories.data ?? [];
  const subcategoryCount = topLevel.reduce((sum, c) => sum + c.children.length, 0);

  return (
    <PageShell
      size="md"
      title="Categories"
      description="Vendors list products under a subcategory, or directly under a category that has none."
      actions={
        <>
          <Pill>{topLevel.length} categories</Pill>
          <Pill>{subcategoryCount} subcategories</Pill>
        </>
      }
    >
      <Card>
        <h2 className="mb-4 text-lg font-semibold text-text-primary">New category</h2>
        <NewCategoryForm
          topLevel={topLevel}
          onCreated={(category) => {
            setNotice(`Added ${category.name}.`);
            categories.reload();
          }}
        />
      </Card>

      {notice && <p className="text-sm font-medium text-status-delivered">{notice}</p>}
      {categories.error && <ErrorText>{categories.error}</ErrorText>}

      {categories.isLoading && !categories.data ? (
        <LoadingText>Loading categories…</LoadingText>
      ) : topLevel.length === 0 ? (
        <EmptyText>No categories yet.</EmptyText>
      ) : (
        <ul className="flex flex-col gap-4">
          {topLevel.map((category) => (
            <TopLevelCard
              key={category.id}
              category={category}
              topLevel={topLevel}
              onChanged={categories.reload}
            />
          ))}
        </ul>
      )}
    </PageShell>
  );
}
