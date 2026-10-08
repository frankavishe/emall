import type { Category } from "@/lib/api-client";

/** `<option>`s for a category `<select>`, grouping subcategories under their parent.
 *
 * A top-level category with subcategories becomes an `<optgroup>`. Vendors must pick one of its
 * subcategories, so the parent itself is only selectable when `selectableParents` is set (the
 * catalog filter, where it means "this category and everything under it"). */
export function CategoryOptions({
  categories,
  selectableParents = false,
}: {
  categories: Category[];
  selectableParents?: boolean;
}) {
  return (
    <>
      {categories.map((category) => {
        const children = category.children ?? [];
        if (children.length === 0) {
          return (
            <option key={category.slug} value={category.slug}>
              {category.name}
            </option>
          );
        }
        return (
          <optgroup key={category.slug} label={category.name}>
            {selectableParents && <option value={category.slug}>All {category.name}</option>}
            {children.map((child) => (
              <option key={child.slug} value={child.slug}>
                {child.name}
              </option>
            ))}
          </optgroup>
        );
      })}
    </>
  );
}

/** The first category a vendor may list a product under (a childless top-level category or a
 * subcategory), used to preselect the picker. */
export function firstPickableCategory(categories: Category[]): string {
  for (const category of categories) {
    const children = category.children ?? [];
    if (children.length === 0) return category.slug;
    return children[0].slug;
  }
  return "";
}
