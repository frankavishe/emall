/**
 * fetch wrapper (task T018). Attaches the in-memory access token, always sends the httpOnly
 * refresh cookie along (`credentials: "include"`), and on a 401 calls `/api/auth/refresh` once
 * before retrying the original request — Constitution Principle III / research.md §7.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// Held in a module-level variable, not localStorage — auth-context.tsx keeps this in sync with
// its own React state whenever the token changes.
let accessToken: string | null = null;

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

/**
 * A user-facing message for a failed request: the `detail` if there is one, otherwise the first
 * DRF field error (e.g. `{"email": ["..."]}`), otherwise `fallback`.
 */
export function errorMessage(
  err: unknown,
  fallback = "Something went wrong. Please try again.",
): string {
  if (!(err instanceof ApiError)) return fallback;
  const body = err.body;
  if (body && typeof body === "object" && !("detail" in body)) {
    for (const value of Object.values(body as Record<string, unknown>)) {
      const first = Array.isArray(value) ? value[0] : value;
      if (typeof first === "string") return first;
    }
  }
  return err.message;
}

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, body: unknown) {
    const detail =
      body && typeof body === "object" && "detail" in body
        ? String((body as { detail: unknown }).detail)
        : `Request failed with status ${status}`;
    super(detail);
    this.status = status;
    this.body = body;
  }
}

async function parseBody(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function buildRequestInit(options: RequestInit): RequestInit {
  const headers = new Headers(options.headers);
  // FormData bodies (e.g. product image uploads) must NOT get an explicit Content-Type — the
  // browser sets multipart/form-data with the correct boundary itself.
  if (!headers.has("Content-Type") && options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }
  return { ...options, headers, credentials: "include" };
}

/**
 * Calls `/api/auth/refresh`; on success updates the in-memory access token and returns it.
 * Returns null without throwing when the API is unreachable, so an outage reads as "no session"
 * instead of an unhandled rejection. The current token is kept in that case — only an actual
 * non-OK response from the API clears it.
 */
export async function refreshAccessToken(): Promise<string | null> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
      method: "POST",
      credentials: "include",
    });
  } catch {
    return null;
  }
  if (!response.ok) {
    setAccessToken(null);
    return null;
  }
  const body = (await parseBody(response)) as { access?: string } | null;
  setAccessToken(body?.access ?? null);
  return accessToken;
}

/** `path` is relative to `NEXT_PUBLIC_API_BASE_URL`, e.g. `/api/auth/me`. */
export async function apiFetch<T = unknown>(
  path: string,
  options: RequestInit = {},
  _isRetry = false,
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, buildRequestInit(options));

  if (response.status === 401 && !_isRetry && path !== "/api/auth/refresh") {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      return apiFetch<T>(path, options, true);
    }
  }

  const body = await parseBody(response);
  if (!response.ok) {
    throw new ApiError(response.status, body);
  }
  return body as T;
}

export type ShippingDetails = {
  recipient_name: string;
  address_line: string;
  city: string;
  region: string;
  postal_code: string;
  country: string;
  phone: string;
};

/** The rider assigned to deliver an order line. */
export type RiderBrief = { id: number; name: string; phone: string };

export type OrderItem = {
  id: number;
  product: { id: number; name: string };
  shop_name: string;
  quantity: number;
  unit_price: string;
  subtotal: string;
  status: string;
  rider: RiderBrief | null;
};

export type OrderDetail = {
  id: number;
  placed_at: string;
  status: string;
  total: string;
  shipping: ShippingDetails;
  items: OrderItem[];
  payment: { method: string; status: string };
};

export type OrderSummary = {
  id: number;
  placed_at: string;
  status: string;
  total: string;
};

export type PaginatedResponse<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export type CatalogProduct = {
  id: number;
  name: string;
  price: string;
  category: string | null;
  in_stock: boolean;
  shop_name: string;
  shop_logo_url: string | null;
  thumbnail_url: string | null;
  average_rating: number | null;
  review_count: number;
};

export type Category = { name: string; slug: string };

export type ListProductsOptions = {
  limit?: number;
  q?: string;
  category?: string;
  minPrice?: string;
  maxPrice?: string;
};

/** `GET /api/catalog/products`; `limit` maps to the opt-in `?page_size=` (task T005,
 * contracts/homepage-api.md) — omit it to get the existing default page of 20. */
export async function listProducts(
  options?: number | ListProductsOptions,
): Promise<PaginatedResponse<CatalogProduct>> {
  const { limit, q, category, minPrice, maxPrice } =
    typeof options === "number" ? { limit: options } : (options ?? {});

  const params = new URLSearchParams();
  if (limit) params.set("page_size", String(limit));
  if (q?.trim()) params.set("q", q.trim());
  if (category) params.set("category", category);
  if (minPrice?.trim()) params.set("min_price", minPrice.trim());
  if (maxPrice?.trim()) params.set("max_price", maxPrice.trim());

  const query = params.toString();
  return apiFetch<PaginatedResponse<CatalogProduct>>(
    `/api/catalog/products${query ? `?${query}` : ""}`,
  );
}

/** `GET /api/catalog/categories`. */
export async function listCategories(): Promise<Category[]> {
  return apiFetch<Category[]>("/api/catalog/categories");
}

/** `POST /api/checkout` (task T038, contracts/cart-checkout-api.md). */
export async function checkout(
  shippingData: ShippingDetails,
  paymentMethod: string,
): Promise<OrderDetail> {
  return apiFetch<OrderDetail>("/api/checkout", {
    method: "POST",
    body: JSON.stringify({ shipping: shippingData, payment_method: paymentMethod }),
  });
}

/** `GET /api/orders` (task T052, contracts/cart-checkout-api.md). */
export async function listOrders(page = 1): Promise<PaginatedResponse<OrderSummary>> {
  return apiFetch<PaginatedResponse<OrderSummary>>(`/api/orders?page=${page}`);
}

/** `GET /api/orders/{id}` (task T052, contracts/cart-checkout-api.md). */
export async function getOrder(orderId: number | string): Promise<OrderDetail> {
  return apiFetch<OrderDetail>(`/api/orders/${orderId}`);
}

export type VendorOrderItem = {
  id: number;
  order_id: number;
  product: { id: number; name: string };
  quantity: number;
  unit_price: string;
  status: string;
  shipping: ShippingDetails;
  rider: RiderBrief | null;
};

/** `GET /api/vendor/order-items` (task T015, contracts/order-fulfillment-api.md). `limit` maps to
 * the opt-in `?page_size=` (task T014, contracts/homepage-api.md) — omit it to get the existing
 * default page of 20. */
export async function listVendorOrderItems(
  page = 1,
  limit?: number,
): Promise<PaginatedResponse<VendorOrderItem>> {
  const limitParam = limit ? `&page_size=${limit}` : "";
  return apiFetch<PaginatedResponse<VendorOrderItem>>(
    `/api/vendor/order-items?page=${page}${limitParam}`,
  );
}

/** `PATCH /api/vendor/order-items/{id}/status` (task T015, contracts/order-fulfillment-api.md). */
export async function updateOrderItemStatus(
  itemId: number,
  newStatus: string,
): Promise<VendorOrderItem> {
  return apiFetch<VendorOrderItem>(`/api/vendor/order-items/${itemId}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status: newStatus }),
  });
}

export type AdminOrderItem = {
  id: number;
  order_id: number;
  product: { id: number; name: string };
  shop: { id: number; name: string };
  quantity: number;
  unit_price: string;
  status: string;
  status_history: { status: string; changed_at: string }[];
  rider: RiderBrief | null;
};

export type AdminShop = {
  id: string;
  name: string;
  status: "PENDING" | "APPROVED" | "REJECTED";
  status_reason: string | null;
  created_at: string;
  owner_name: string;
  owner_email: string;
  logo_url: string | null;
};

/** `GET /api/admin/shops` (task T019, contracts/homepage-api.md). `limit` maps to the opt-in
 * `?page_size=` (task T017) — omit it to get the existing default page of 20. */
export async function listAdminShops(
  status?: string,
  limit?: number,
): Promise<PaginatedResponse<AdminShop>> {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (limit) params.set("page_size", String(limit));
  const query = params.toString() ? `?${params.toString()}` : "";
  return apiFetch<PaginatedResponse<AdminShop>>(`/api/admin/shops${query}`);
}

/** `GET /api/admin/order-items` (task T026, contracts/order-fulfillment-api.md). `limit` maps to
 * the opt-in `?page_size=` (task T018, contracts/homepage-api.md) — omit it to get the existing
 * default page of 20. */
export async function listAdminOrderItems(
  page = 1,
  limit?: number,
): Promise<PaginatedResponse<AdminOrderItem>> {
  const limitParam = limit ? `&page_size=${limit}` : "";
  return apiFetch<PaginatedResponse<AdminOrderItem>>(
    `/api/admin/order-items?page=${page}${limitParam}`,
  );
}

export type Review = {
  id: number;
  product: number;
  rating: number;
  comment: string;
  created_at: string;
  updated_at: string;
};

/** `POST /api/feedback/products/{id}/review` (task T016, contracts/feedback-api.md). Creates or
 * updates the requesting Customer's own review (upsert). */
export async function submitReview(
  productId: number,
  data: { rating: number; comment?: string },
): Promise<Review> {
  return apiFetch<Review>(`/api/feedback/products/${productId}/review`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

/** `DELETE /api/feedback/products/{id}/review` (task T016, contracts/feedback-api.md). */
export async function deleteReview(productId: number): Promise<void> {
  await apiFetch<void>(`/api/feedback/products/${productId}/review`, { method: "DELETE" });
}

export type VendorReview = {
  id: number;
  product: { id: number; name: string };
  customer_display_name: string;
  rating: number;
  comment: string;
  created_at: string;
};

/** `GET /api/vendor/reviews` (task T032, contracts/feedback-api.md). */
/** `PUT /api/vendor/shops/:id/logo` — upload or replace a shop's logo (multipart). */
export async function uploadShopLogo(shopId: string, file: File): Promise<void> {
  const formData = new FormData();
  formData.set("logo", file);
  await apiFetch(`/api/vendor/shops/${shopId}/logo`, { method: "PUT", body: formData });
}

/** `DELETE /api/vendor/shops/:id/logo` */
export async function removeShopLogo(shopId: string): Promise<void> {
  await apiFetch(`/api/vendor/shops/${shopId}/logo`, { method: "DELETE" });
}

export async function listVendorReviews(page = 1): Promise<PaginatedResponse<VendorReview>> {
  return apiFetch<PaginatedResponse<VendorReview>>(`/api/vendor/reviews?page=${page}`);
}

export type AdminReview = {
  id: number;
  product: { id: number; name: string };
  shop: { id: number; name: string };
  customer: { id: number; email: string };
  rating: number;
  comment: string;
  created_at: string;
};

/** `GET /api/admin/reviews` (task T040, contracts/feedback-api.md). */
export async function listAdminReviews(page = 1): Promise<PaginatedResponse<AdminReview>> {
  return apiFetch<PaginatedResponse<AdminReview>>(`/api/admin/reviews?page=${page}`);
}

/** `DELETE /api/admin/reviews/{id}` (task T040, contracts/feedback-api.md). */
export async function deleteReviewAsAdmin(reviewId: number): Promise<void> {
  await apiFetch<void>(`/api/admin/reviews/${reviewId}`, { method: "DELETE" });
}

export type VehicleType = "MOTORCYCLE" | "BICYCLE" | "CAR" | "VAN" | "OTHER";

export const VEHICLE_TYPES: { value: VehicleType; label: string }[] = [
  { value: "MOTORCYCLE", label: "Motorcycle" },
  { value: "BICYCLE", label: "Bicycle" },
  { value: "CAR", label: "Car" },
  { value: "VAN", label: "Van" },
  { value: "OTHER", label: "Other" },
];

export type AdminRider = {
  id: number;
  name: string;
  email: string;
  is_active: boolean;
  phone: string;
  vehicle_type: VehicleType;
  plate_number: string;
  active_delivery_count: number;
  date_joined: string;
};

export type NewRider = {
  name: string;
  email: string;
  password: string;
  phone: string;
  vehicle_type: VehicleType;
  plate_number: string;
};

/** `GET /api/admin/riders`; `isActive` filters to active/inactive riders. */
export async function listAdminRiders(
  options: { isActive?: boolean; page?: number; limit?: number } = {},
): Promise<PaginatedResponse<AdminRider>> {
  const params = new URLSearchParams();
  if (options.isActive !== undefined) params.set("is_active", String(options.isActive));
  if (options.page) params.set("page", String(options.page));
  if (options.limit) params.set("page_size", String(options.limit));
  const query = params.toString() ? `?${params.toString()}` : "";
  return apiFetch<PaginatedResponse<AdminRider>>(`/api/admin/riders${query}`);
}

/** `POST /api/admin/riders` — an admin registers a rider with a temporary password. */
export async function createRider(data: NewRider): Promise<AdminRider> {
  return apiFetch<AdminRider>("/api/admin/riders", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

/** `PATCH /api/admin/riders/{id}` — edit details, (de)activate, or set a new password. */
export async function updateRider(
  riderId: number,
  data: Partial<Omit<NewRider, "email">> & { is_active?: boolean },
): Promise<AdminRider> {
  return apiFetch<AdminRider>(`/api/admin/riders/${riderId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

/** `POST /api/admin/order-items/{id}/rider` — `null` unassigns. */
export async function assignOrderItemRider(
  itemId: number,
  riderId: number | null,
): Promise<AdminOrderItem> {
  return apiFetch<AdminOrderItem>(`/api/admin/order-items/${itemId}/rider`, {
    method: "POST",
    body: JSON.stringify({ rider_id: riderId }),
  });
}

export type RiderDelivery = {
  id: number;
  order_id: number;
  product: { id: number; name: string };
  quantity: number;
  status: string;
  pickup: { shop_name: string };
  dropoff: ShippingDetails;
  rider_assigned_at: string | null;
};

/** `GET /api/rider/deliveries` — the rider's own active (default) or completed deliveries. */
export async function listRiderDeliveries(
  scope: "active" | "completed" = "active",
  page = 1,
): Promise<PaginatedResponse<RiderDelivery>> {
  return apiFetch<PaginatedResponse<RiderDelivery>>(
    `/api/rider/deliveries?scope=${scope}&page=${page}`,
  );
}

/** `PATCH /api/rider/deliveries/{id}/status` — SHIPPED (picked up) or DELIVERED. */
export async function updateDeliveryStatus(
  itemId: number,
  newStatus: "SHIPPED" | "DELIVERED",
): Promise<RiderDelivery> {
  return apiFetch<RiderDelivery>(`/api/rider/deliveries/${itemId}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status: newStatus }),
  });
}
