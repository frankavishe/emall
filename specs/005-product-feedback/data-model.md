# Data Model: Product Feedback & Reviews

## Review (new — `apps.feedback.models.Review`)

One Customer's feedback on one Product. At most one row per (customer, product) pair.

| Field | Type | Notes |
|---|---|---|
| `id` | PK (auto) | |
| `customer` | FK → `settings.AUTH_USER_MODEL`, `on_delete=CASCADE`, `related_name="reviews"` | The reviewing Customer. Deleting a user's account removes their reviews (no orphaned reviews attributed to a deleted account). |
| `product` | FK → `catalog.Product`, `on_delete=CASCADE`, `related_name="reviews"` | The reviewed Product. Deleting a product removes its reviews (matches `catalog.Product`'s existing soft-delete-first pattern — a hard-deleted product has no page for reviews to attach to anyway). |
| `rating` | `PositiveSmallIntegerField` | 1-5 inclusive, enforced by a `CheckConstraint` (mirrors `catalog.Product`'s `price__gte=0` constraint pattern). |
| `comment` | `TextField(blank=True, default="")` | Optional written comment (FR-001: rating required, comment optional). |
| `created_at` | `DateTimeField(auto_now_add=True)` | |
| `updated_at` | `DateTimeField(auto_now=True)` | Set on every edit (research.md §3 upsert). |

**Constraints**:
- `UniqueConstraint(fields=["customer", "product"], name="unique_review_per_customer_product")`
  — the actual database-level guarantee behind FR-003.
- `CheckConstraint(condition=Q(rating__gte=1) & Q(rating__lte=5), name="review_rating_range")`.

**Validation rules (enforced in the serializer/view, not just the DB constraints)**:
- A Review can only be created/updated by its `customer` if that customer has at least one
  `orders.OrderItem` with `product=<this product>`, `order__customer=<this customer>`, and
  `status=OrderItem.Status.DELIVERED` (FR-001/FR-002; research.md §2 — re-checked live, not cached
  on the Review row).
- `rating` is required on create; `comment` defaults to empty string when omitted.

**State transitions**: None — a Review has no lifecycle/status field. It exists (created/updated by
its owning Customer) or it doesn't (deleted by an Administrator, or cascade-deleted with its
Customer/Product).

**Relationships**:
- `catalog.Product.reviews` (reverse of `Review.product`) — used by the average-rating/count
  aggregate (research.md §4) and by the public product detail serializer.
- `Review` references `orders.OrderItem` only through a live query at write time (research.md §2),
  not a stored foreign key — no schema coupling to a specific order line.

## Product Rating Summary (derived, not a stored entity)

Not a database table. Computed on read as `Review.objects.filter(product=product).aggregate(
average_rating=Avg("rating"), review_count=Count("id"))` (research.md §4), surfaced as two extra
fields (`average_rating`, `review_count`) on the existing `CatalogProductDetailSerializer` and
`CatalogProductListSerializer` output. `average_rating` is `null`/absent-equivalent and
`review_count` is `0` when a product has no reviews (spec User Story 2, Scenario 2).

## Migration notes

- One new migration in `apps/feedback/migrations/`: creates `Review` with the FK/constraints
  above. No changes to any existing app's schema (`catalog.Product`, `orders.OrderItem` are read
  from, not modified).
- `apps/feedback/` must be added to `INSTALLED_APPS` in `config/settings.py`.
