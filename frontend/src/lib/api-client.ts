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

/** Calls `/api/auth/refresh`; on success updates the in-memory access token and returns it. */
export async function refreshAccessToken(): Promise<string | null> {
  const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
    method: "POST",
    credentials: "include",
  });
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

export type OrderItem = {
  id: number;
  product: { id: number; name: string };
  shop_name: string;
  quantity: number;
  unit_price: string;
  subtotal: string;
  status: string;
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
};

/** `GET /api/vendor/order-items` (task T015, contracts/order-fulfillment-api.md). */
export async function listVendorOrderItems(page = 1): Promise<PaginatedResponse<VendorOrderItem>> {
  return apiFetch<PaginatedResponse<VendorOrderItem>>(`/api/vendor/order-items?page=${page}`);
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
};

/** `GET /api/admin/order-items` (task T026, contracts/order-fulfillment-api.md). */
export async function listAdminOrderItems(page = 1): Promise<PaginatedResponse<AdminOrderItem>> {
  return apiFetch<PaginatedResponse<AdminOrderItem>>(`/api/admin/order-items?page=${page}`);
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
