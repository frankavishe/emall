/**
 * fetch wrapper (task T018). Attaches the in-memory access token, always sends the httpOnly
 * refresh cookie along (`credentials: "include"`), and on a 401 calls `/api/auth/refresh` once
 * before retrying the original request — Constitution Principle III / research.md §7.
 */

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// Held in a module-level variable, not localStorage — auth-context.tsx keeps this in sync with
// its own React state whenever the token changes.
let accessToken: string | null = null;
const accessTokenListeners = new Set<(token: string | null) => void>();

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string | null): void {
  if (token === accessToken) return;
  accessToken = token;
  accessTokenListeners.forEach((listener) => listener(token));
}

/** Calls `listener` whenever the access token changes (sign-in, refresh, sign-out). Returns an
 * unsubscribe function. Used by the realtime socket to re-authenticate. */
export function onAccessTokenChange(listener: (token: string | null) => void): () => void {
  accessTokenListeners.add(listener);
  return () => {
    accessTokenListeners.delete(listener);
  };
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

// The refresh in flight, shared by every caller. The backend rotates the refresh cookie and
// blacklists the old one, so a second concurrent refresh sending that same cookie would be
// rejected and wipe the token the first one just obtained.
let refreshInFlight: Promise<string | null> | null = null;

/**
 * Calls `/api/auth/refresh`; on success updates the in-memory access token and returns it.
 * Concurrent calls share one request. Returns null without throwing when the API is
 * unreachable, so an outage reads as "no session" instead of an unhandled rejection. The
 * current token is kept in that case — only an actual non-OK response from the API clears it.
 */
export function refreshAccessToken(): Promise<string | null> {
  refreshInFlight ??= doRefresh().finally(() => {
    refreshInFlight = null;
  });
  return refreshInFlight;
}

async function doRefresh(): Promise<string | null> {
  const tokenBefore = accessToken;
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
    // Leave a token set meanwhile (e.g. by a login) alone; only the one that failed goes.
    if (accessToken === tokenBefore) setAccessToken(null);
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

/** Like `apiFetch`, but for a file response (e.g. a PDF report): resolves to its bytes. */
export async function apiFetchBlob(path: string, _isRetry = false): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}${path}`, buildRequestInit({}));

  if (response.status === 401 && !_isRetry) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      return apiFetchBlob(path, true);
    }
  }

  if (!response.ok) {
    throw new ApiError(response.status, await parseBody(response));
  }
  return response.blob();
}

/** The typed delivery address a customer enters at checkout. */
export type ShippingAddress = {
  recipient_name: string;
  address_line: string;
  phone: string;
};

/** The rest of an order's address as the API returns it. Checkout no longer sends these: the
 * server defaults them to Dar es Salaam, Tanzania. */
type ShippingLocality = {
  city: string;
  region: string;
  postal_code: string;
  country: string;
};

/** A map pin, in decimal degrees. */
export type LatLng = { latitude: number; longitude: number };

/** An order's delivery address as returned by the API. The pin is null only on orders placed
 * before delivery pricing existed (007-delivery-fee). */
export type ShippingDetails = ShippingAddress &
  ShippingLocality & {
    latitude: string | null;
    longitude: string | null;
  };

/** One shop's delivery leg: the distance from the shop to the pin and the fee for it. */
export type DeliveryLeg = {
  shop_id: number;
  shop_name: string;
  distance_km: string;
  fee: string;
};

/** Item subtotal, delivery fee and their sum (`total`), as decimal strings in TZS. */
export type OrderTotals = {
  items_subtotal: string;
  delivery_fee: string;
  total: string;
};

export type DeliveryQuote = OrderTotals & { legs: DeliveryLeg[] };

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

export type OrderDetail = OrderTotals & {
  id: number;
  placed_at: string;
  status: string;
  shipping: ShippingDetails;
  items: OrderItem[];
  deliveries: DeliveryLeg[];
  payment: OrderPayment;
  /** Guest orders only (guest checkout): the private token behind `/orders/track/{token}`. */
  access_token?: string;
};

/** AzamPay MNO provider names, sent to the API as-is. */
export type MobileMoneyProvider = "Mpesa" | "Tigo" | "Airtel" | "Halopesa" | "Azampesa";

export const MOBILE_MONEY_PROVIDERS: { value: MobileMoneyProvider; label: string }[] = [
  { value: "Mpesa", label: "M-Pesa (Vodacom)" },
  { value: "Tigo", label: "Mixx by Yas (Tigo Pesa)" },
  { value: "Airtel", label: "Airtel Money" },
  { value: "Halopesa", label: "HaloPesa" },
  { value: "Azampesa", label: "AzamPesa" },
];

const PAYMENT_METHOD_LABELS: Record<string, string> = {
  card: "Card",
  mobile_money: "Mobile money",
  cod: "Cash on delivery",
  lipa_namba: "Lipa Namba",
};

/** A payment method's display name, e.g. `cod` -> "Cash on delivery". */
export function paymentMethodLabel(method: string): string {
  return PAYMENT_METHOD_LABELS[method] ?? method.replace(/_/g, " ");
}

export type OrderPayment = {
  /** `card`, `mobile_money`, `cod` (cash on delivery) or `lipa_namba`. */
  method: string;
  /** PENDING (mobile money awaiting the customer's PIN, Lipa Namba awaiting verification, cash
   * on delivery not yet collected), SUCCEEDED or FAILED. */
  status: string;
  amount: string;
  provider: MobileMoneyProvider | "";
  /** Masked, e.g. `25571****678`. */
  msisdn: string;
  failure_reason: string;
  /** Lipa Namba only: the transaction ID the customer gave. */
  payer_reference: string;
};

export type OrderSummary = OrderTotals & {
  id: number;
  placed_at: string;
  status: string;
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
  stock_quantity: number;
  low_stock: boolean;
  shop_name: string;
  shop_logo_url: string | null;
  thumbnail_url: string | null;
  average_rating: number | null;
  review_count: number;
};

/** Public category tree node: top-level categories carry their subcategories in `children`. */
export type Category = { name: string; slug: string; children?: Category[] };

export type ListProductsOptions = {
  limit?: number;
  q?: string;
  category?: string;
  minPrice?: string;
  maxPrice?: string;
  /** Restrict to one shop's products (the public shop page). */
  shop?: string | number;
  page?: number;
};

/** `GET /api/catalog/products`; `limit` maps to the opt-in `?page_size=` (task T005,
 * contracts/homepage-api.md) — omit it to get the existing default page of 20. */
export async function listProducts(
  options?: number | ListProductsOptions,
): Promise<PaginatedResponse<CatalogProduct>> {
  const { limit, q, category, minPrice, maxPrice, shop, page } =
    typeof options === "number" ? { limit: options } : (options ?? {});

  const params = new URLSearchParams();
  if (limit) params.set("page_size", String(limit));
  if (q?.trim()) params.set("q", q.trim());
  if (category) params.set("category", category);
  if (minPrice?.trim()) params.set("min_price", minPrice.trim());
  if (maxPrice?.trim()) params.set("max_price", maxPrice.trim());
  if (shop) params.set("shop", String(shop));
  if (page && page > 1) params.set("page", String(page));

  const query = params.toString();
  return apiFetch<PaginatedResponse<CatalogProduct>>(
    `/api/catalog/products${query ? `?${query}` : ""}`,
  );
}

/** `GET /api/catalog/products/:id/related` — up to 8 products for the product page, unpaginated. */
export async function listRelatedProducts(productId: number): Promise<CatalogProduct[]> {
  return apiFetch<CatalogProduct[]>(`/api/catalog/products/${productId}/related`);
}

/** Public shop profile — what a shop page and themed product pages need. */
export type CatalogShop = {
  id: number;
  name: string;
  logo_url: string | null;
  primary_color: string;
  accent_color: string;
  /** Only on `GET /api/catalog/shops/:id`, not on the shop nested in product payloads. */
  description?: string;
};

/** One card on the public merchants directory. */
export type CatalogShopListItem = CatalogShop & { description: string; product_count: number };

/** `GET /api/catalog/shops` — approved shops, alphabetically, paginated. */
export async function listPublicShops(page = 1): Promise<PaginatedResponse<CatalogShopListItem>> {
  const query = page > 1 ? `?page=${page}` : "";
  return apiFetch<PaginatedResponse<CatalogShopListItem>>(`/api/catalog/shops${query}`);
}

/** `GET /api/catalog/shops/:id` — `404` unless the shop is approved. */
export async function getPublicShop(shopId: number | string): Promise<CatalogShop> {
  return apiFetch<CatalogShop>(`/api/catalog/shops/${shopId}`);
}

/** `GET /api/catalog/categories`. */
export async function listCategories(): Promise<Category[]> {
  return apiFetch<Category[]>("/api/catalog/categories");
}

/** `POST /api/checkout/delivery-quote`: what delivering the current cart to `pin` costs.
 * Advisory only; checkout recomputes it. */
export async function getDeliveryQuote(pin: LatLng): Promise<DeliveryQuote> {
  return apiFetch<DeliveryQuote>("/api/checkout/delivery-quote", {
    method: "POST",
    body: JSON.stringify(pin),
  });
}

export type MobileMoneyDetails = { msisdn: string; provider: MobileMoneyProvider };
/** Lipa Namba: the transaction ID from the customer's payment confirmation SMS. */
export type LipaNambaDetails = { payer_reference: string };

/** A way to pay that checkout offers (`GET /api/payments/methods`). */
export type PaymentMethodOption = {
  method: string;
  label: string;
  /** Lipa Namba only: the mall's till number and the name it shows. */
  till_number?: string;
  till_name?: string;
};

export async function listPaymentMethods(): Promise<PaymentMethodOption[]> {
  return apiFetch<PaymentMethodOption[]>("/api/payments/methods");
}

/** `POST /api/checkout` (task T038, contracts/cart-checkout-api.md). The delivery pin is
 * mandatory; the server prices delivery itself. With `mobile_money` the order comes back
 * `AWAITING_PAYMENT` (HTTP 202) until the customer approves the push on their phone (with
 * `lipa_namba`, until an administrator confirms the payment arrived); a `409`
 * with `code: "payment_pending"` carries the `order_id` already waiting for payment (a guest's
 * carries its `access_token` instead). A guest (no session) must pass `guestEmail`. */
export async function checkout(
  shippingData: ShippingAddress & LatLng,
  paymentMethod: string,
  paymentDetails?: MobileMoneyDetails | LipaNambaDetails,
  guestEmail?: string,
): Promise<OrderDetail> {
  return apiFetch<OrderDetail>("/api/checkout", {
    method: "POST",
    body: JSON.stringify({
      shipping: shippingData,
      payment_method: paymentMethod,
      ...(paymentDetails ?? {}),
      ...(guestEmail ? { email: guestEmail } : {}),
    }),
  });
}

/** Where an order lives in the app: a guest order only by its private token, never its id. */
export function orderPath(order: { id?: number; access_token?: string }): string {
  return order.access_token ? `/orders/track/${order.access_token}` : `/orders/${order.id}`;
}

export type PaymentStatus = {
  order_id: number;
  order_status: string;
  payment_status: string | null;
  failure_reason: string;
};

/** `GET /api/orders/{id}/payment-status` — polled while a mobile-money payment is pending. */
export async function getPaymentStatus(orderId: number | string): Promise<PaymentStatus> {
  return apiFetch<PaymentStatus>(`/api/orders/${orderId}/payment-status`);
}

/** `GET /api/orders/track/{token}/payment-status`: a guest order's payment poll. */
export async function getGuestPaymentStatus(token: string): Promise<PaymentStatus> {
  return apiFetch<PaymentStatus>(`/api/orders/track/${encodeURIComponent(token)}/payment-status`);
}

/** A USSD push waiting on the simulated phone (dev-only AzamPay sandbox simulator). */
export type SimulatedPush = {
  reference: string;
  order_id: number;
  msisdn: string;
  provider: MobileMoneyProvider;
  amount: string;
  created_at: string;
};

/** True when the local AzamPay simulator UI should be offered (never in production builds). */
export const PAYMENT_SIMULATOR_ENABLED = process.env.NEXT_PUBLIC_PAYMENT_SIMULATOR === "true";

/** `GET /api/dev/azampay-sim/pushes` — 404s unless the backend runs the simulator. */
export async function listSimulatedPushes(): Promise<SimulatedPush[]> {
  return apiFetch<SimulatedPush[]>("/api/dev/azampay-sim/pushes");
}

/** Approve (with the PIN) or reject a simulated push; the backend then runs the same callback
 * handler AzamPay's real callback goes through. */
export async function decideSimulatedPush(
  reference: string,
  decision: "approve" | "reject",
  pin?: string,
): Promise<{ outcome: string }> {
  return apiFetch<{ outcome: string }>(`/api/dev/azampay-sim/pushes/${reference}/${decision}`, {
    method: "POST",
    body: JSON.stringify(pin ? { pin } : {}),
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

/** `GET /api/orders/track/{token}`: a guest order, reached only through its private token. */
export async function getGuestOrder(token: string): Promise<OrderDetail> {
  return apiFetch<OrderDetail>(`/api/orders/track/${encodeURIComponent(token)}`);
}

export type VendorOrderItem = {
  id: number;
  order_id: number;
  product: { id: number; name: string };
  quantity: number;
  unit_price: string;
  commission_rate: string;
  commission_amount: string;
  vendor_earning: string;
  payout_id: number | null;
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
): Promise<AdminOrderItem> {
  return apiFetch<AdminOrderItem>(`/api/admin/order-items/${itemId}/status`, {
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
  commission_rate: string;
  commission_amount: string;
  vendor_earning: string;
  payout_id: number | null;
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
export type ProfileUpdate = { name?: string; phone?: string };

/** `PATCH /api/auth/me`: the signed-in user's own name and phone. Email is not editable. */
export async function updateMyProfile(body: ProfileUpdate): Promise<void> {
  await apiFetch("/api/auth/me", { method: "PATCH", body: JSON.stringify(body) });
}

/** `PUT /api/auth/me/avatar` — upload or replace the signed-in user's photo (multipart). */
export async function uploadMyAvatar(file: File): Promise<void> {
  const formData = new FormData();
  formData.set("avatar", file);
  await apiFetch("/api/auth/me/avatar", { method: "PUT", body: formData });
}

/** `DELETE /api/auth/me/avatar` */
export async function removeMyAvatar(): Promise<void> {
  await apiFetch("/api/auth/me/avatar", { method: "DELETE" });
}

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

export type ShopLocation = LatLng & { location_address: string };

/** `PUT /api/vendor/shops/:id/location`: the shop's pickup pin and address, which delivery
 * fees are measured from. */
export async function updateShopLocation(shopId: string, location: ShopLocation): Promise<void> {
  await apiFetch(`/api/vendor/shops/${shopId}/location`, {
    method: "PUT",
    body: JSON.stringify(location),
  });
}

/** `PUT /api/admin/shops/:id/location`: an Administrator sets any shop's pickup location. */
export async function updateAdminShopLocation(
  shopId: number | string,
  location: ShopLocation,
): Promise<void> {
  await apiFetch(`/api/admin/shops/${shopId}/location`, {
    method: "PUT",
    body: JSON.stringify(location),
  });
}

/** `PATCH /api/vendor/shops/:id/theme` — each color is `#rrggbb`, or `""` to reset it to the
 * MangiMall default. */
export async function updateShopTheme(
  shopId: string,
  theme: { primary_color?: string; accent_color?: string },
): Promise<void> {
  await apiFetch(`/api/vendor/shops/${shopId}/theme`, {
    method: "PATCH",
    body: JSON.stringify(theme),
  });
}

/** `PATCH /api/vendor/shops/:id/name` — must not be taken by another shop. */
export async function updateShopName(shopId: string, name: string): Promise<void> {
  await apiFetch(`/api/vendor/shops/${shopId}/name`, {
    method: "PATCH",
    body: JSON.stringify({ name }),
  });
}

/** Longest storefront description the API accepts. */
export const MAX_SHOP_DESCRIPTION_LENGTH = 1000;

/** `PATCH /api/vendor/shops/:id/description` — plain text, `""` to clear. */
export async function updateShopDescription(shopId: string, description: string): Promise<void> {
  await apiFetch(`/api/vendor/shops/${shopId}/description`, {
    method: "PATCH",
    body: JSON.stringify({ description }),
  });
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

export type AdminCustomer = {
  id: number;
  name: string;
  email: string;
  is_vendor: boolean;
  is_email_verified: boolean;
  is_active: boolean;
  date_joined: string;
  order_count: number;
  total_spent: string;
  shop_count: number;
};

export type AdminCustomerDetail = AdminCustomer & {
  recent_orders: { id: number; placed_at: string; item_count: number; total: string }[];
};

/** `GET /api/admin/customers` — shopper accounts (vendors included), newest first. */
export async function listAdminCustomers(
  options: { q?: string; isActive?: boolean; page?: number } = {},
): Promise<PaginatedResponse<AdminCustomer>> {
  const params = new URLSearchParams();
  if (options.q?.trim()) params.set("q", options.q.trim());
  if (options.isActive !== undefined) params.set("is_active", String(options.isActive));
  if (options.page && options.page > 1) params.set("page", String(options.page));
  const query = params.toString() ? `?${params.toString()}` : "";
  return apiFetch<PaginatedResponse<AdminCustomer>>(`/api/admin/customers${query}`);
}

export async function getAdminCustomer(customerId: number | string): Promise<AdminCustomerDetail> {
  return apiFetch<AdminCustomerDetail>(`/api/admin/customers/${customerId}`);
}

/** `PATCH /api/admin/customers/{id}` — blocking also logs the customer out everywhere. */
export async function updateCustomer(
  customerId: number,
  data: { is_active: boolean },
): Promise<AdminCustomerDetail> {
  return apiFetch<AdminCustomerDetail>(`/api/admin/customers/${customerId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export type AdminCategory = {
  id: number;
  name: string;
  slug: string;
  parent: number | null;
  product_count: number;
  can_delete: boolean;
  children: AdminCategory[];
};

/** `GET /api/admin/categories` — top-level categories with nested subcategories. */
export async function listAdminCategories(): Promise<AdminCategory[]> {
  return apiFetch<AdminCategory[]>("/api/admin/categories");
}

export async function createCategory(data: {
  name: string;
  parent: number | null;
}): Promise<AdminCategory> {
  return apiFetch<AdminCategory>("/api/admin/categories", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateCategory(
  categoryId: number,
  data: { name?: string; parent?: number | null },
): Promise<AdminCategory> {
  return apiFetch<AdminCategory>(`/api/admin/categories/${categoryId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteCategory(categoryId: number): Promise<void> {
  await apiFetch(`/api/admin/categories/${categoryId}`, { method: "DELETE" });
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
  pickup: {
    shop_name: string;
    address: string;
    latitude: string | null;
    longitude: string | null;
  };
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

// --- Mall finance: commission, payouts, admin oversight ---------------------------------------

/** Money figures shared by the platform summary, shop balances and vendor earnings. Decimal
 * strings, TZS. */
export type BalanceFigures = {
  gross_sales: string;
  commission_earned: string;
  commission_pending: string;
  pending_earnings: string;
  available_balance: string;
  in_payout: string;
  paid_out: string;
};

export type PlatformSummary = BalanceFigures & {
  order_count: number;
  line_count: number;
  default_commission_rate: string;
  /** Delivery fees collected: the mall's own revenue, outside every shop balance. */
  delivery_revenue: string;
};

export type DateRange = { from?: string; to?: string };

function dateRangeQuery(range: DateRange = {}): URLSearchParams {
  const params = new URLSearchParams();
  if (range.from) params.set("from", range.from);
  if (range.to) params.set("to", range.to);
  return params;
}

function withQuery(path: string, params: URLSearchParams): string {
  const query = params.toString();
  return query ? `${path}?${query}` : path;
}

export async function getFinanceSummary(range?: DateRange): Promise<PlatformSummary> {
  return apiFetch<PlatformSummary>(withQuery("/api/admin/finance/summary", dateRangeQuery(range)));
}

/** PDF of the finance summary for `range`, plus every shop's balance. */
export async function downloadFinanceReport(range?: DateRange): Promise<Blob> {
  return apiFetchBlob(withQuery("/api/admin/finance/report.pdf", dateRangeQuery(range)));
}

export type DeliveryPricing = {
  delivery_base_fee: string;
  delivery_per_km_fee: string;
  delivery_min_fee: string;
  delivery_max_distance_km: string;
  delivery_road_factor: string;
};

export type PlatformSettings = DeliveryPricing & {
  default_commission_rate: string;
  updated_at: string;
};

export async function getFinanceSettings(): Promise<PlatformSettings> {
  return apiFetch<PlatformSettings>("/api/admin/finance/settings");
}

export async function updateDefaultCommissionRate(rate: string): Promise<PlatformSettings> {
  return apiFetch<PlatformSettings>("/api/admin/finance/settings", {
    method: "PATCH",
    body: JSON.stringify({ default_commission_rate: rate }),
  });
}

/** `PATCH /api/admin/finance/settings` with any subset of the delivery pricing fields. */
export async function updateDeliveryPricing(
  pricing: Partial<DeliveryPricing>,
): Promise<PlatformSettings> {
  return apiFetch<PlatformSettings>("/api/admin/finance/settings", {
    method: "PATCH",
    body: JSON.stringify(pricing),
  });
}

export type ShopBalance = BalanceFigures & {
  id: number;
  name: string;
  status: "PENDING" | "APPROVED" | "REJECTED";
  logo_url: string | null;
  owner_name: string;
  owner_email: string;
  /** Effective rate (override or mall default). */
  commission_rate: string;
  /** The shop's own override, or null when it uses the mall default. */
  commission_rate_override: string | null;
  has_payout_details: boolean;
};

export async function listShopBalances(page = 1): Promise<PaginatedResponse<ShopBalance>> {
  return apiFetch<PaginatedResponse<ShopBalance>>(`/api/admin/finance/balances?page=${page}`);
}

export async function setShopCommissionRate(
  shopId: number | string,
  rate: string | null,
): Promise<void> {
  await apiFetch(`/api/admin/shops/${shopId}/commission`, {
    method: "PATCH",
    body: JSON.stringify({ commission_rate: rate }),
  });
}

export type AdminShopDetail = {
  id: number;
  name: string;
  status: "PENDING" | "APPROVED" | "REJECTED";
  status_reason: string | null;
  created_at: string;
  status_changed_at: string | null;
  logo_url: string | null;
  description: string;
  owner: { id: number; name: string; email: string };
  commission_rate: string | null;
  payout_network: string;
  payout_phone: string;
  payout_account_name: string;
  latitude: string | null;
  longitude: string | null;
  location_address: string;
  product_count: number;
  published_product_count: number;
  balance: BalanceFigures & { commission_rate: string; commission_rate_is_override: boolean };
};

export async function getAdminShop(shopId: number | string): Promise<AdminShopDetail> {
  return apiFetch<AdminShopDetail>(`/api/admin/shops/${shopId}`);
}

export type PayoutStatus = "PENDING" | "PROCESSING" | "SUCCEEDED" | "FAILED";

export type Payout = {
  id: number;
  reference: string;
  shop: { id: number; name: string };
  amount: string;
  status: PayoutStatus;
  network: string;
  phone: string;
  account_name: string;
  provider_reference: string | null;
  failure_reason: string;
  created_by_name: string | null;
  created_at: string;
  completed_at: string | null;
  line_count: number | null;
};

export type PayoutLine = {
  id: number;
  order_id: number;
  product_name: string;
  quantity: number;
  unit_price: string;
  subtotal: string;
  commission_rate: string;
  commission_amount: string;
  vendor_earning: string;
  status: string;
};

export type PayoutDetail = Payout & { items: PayoutLine[] };

export async function createShopPayout(shopId: number | string): Promise<Payout> {
  return apiFetch<Payout>(`/api/admin/shops/${shopId}/payouts`, { method: "POST" });
}

export async function listAdminPayouts(
  options: { page?: number; shop?: number | string; status?: string } = {},
): Promise<PaginatedResponse<Payout>> {
  const params = new URLSearchParams({ page: String(options.page ?? 1) });
  if (options.shop) params.set("shop", String(options.shop));
  if (options.status) params.set("status", options.status);
  return apiFetch<PaginatedResponse<Payout>>(withQuery("/api/admin/payouts", params));
}

/** PDF of every payout matching the filters (not just one page). */
export async function downloadPayoutsReport(
  options: { shop?: number | string; status?: string } = {},
): Promise<Blob> {
  const params = new URLSearchParams();
  if (options.shop) params.set("shop", String(options.shop));
  if (options.status) params.set("status", options.status);
  return apiFetchBlob(withQuery("/api/admin/payouts/report.pdf", params));
}

export async function getAdminPayout(payoutId: number | string): Promise<PayoutDetail> {
  return apiFetch<PayoutDetail>(`/api/admin/payouts/${payoutId}`);
}

/** PDF statement of one payout and the order lines it paid. */
export async function downloadPayoutReport(payoutId: number | string): Promise<Blob> {
  return apiFetchBlob(`/api/admin/payouts/${payoutId}/report.pdf`);
}

export async function retryPayout(payoutId: number | string): Promise<Payout> {
  return apiFetch<Payout>(`/api/admin/payouts/${payoutId}/retry`, { method: "POST" });
}

/** Who bought an order: a customer account, or a guest (guest checkout, `id` null). */
export type OrderBuyer = { id: number | null; name: string; email: string; is_guest: boolean };

export type AdminTransaction = {
  id: number;
  order_id: number;
  customer: OrderBuyer;
  amount: string;
  method: string;
  status: string;
  transaction_reference: string;
  /** The customer's Lipa Namba transaction ID, or the gateway's reference. */
  provider_reference: string;
  created_at: string;
  commission_total: string;
  shop_count: number;
};

export async function listAdminTransactions(
  options: DateRange & { page?: number; search?: string; status?: string; method?: string } = {},
): Promise<PaginatedResponse<AdminTransaction>> {
  const params = dateRangeQuery(options);
  params.set("page", String(options.page ?? 1));
  if (options.search) params.set("search", options.search);
  if (options.status) params.set("status", options.status);
  if (options.method) params.set("method", options.method);
  return apiFetch<PaginatedResponse<AdminTransaction>>(
    withQuery("/api/admin/transactions", params),
  );
}

/** PDF of every transaction matching the filters (not just one page). */
export async function downloadTransactionsReport(
  options: DateRange & { search?: string; status?: string; method?: string } = {},
): Promise<Blob> {
  const params = dateRangeQuery(options);
  if (options.search) params.set("search", options.search);
  if (options.status) params.set("status", options.status);
  if (options.method) params.set("method", options.method);
  return apiFetchBlob(withQuery("/api/admin/transactions/report.pdf", params));
}

/** One audited action. `actor` is null for system events and anonymous callers. */
export type AuditEvent = {
  id: number;
  created_at: string;
  actor: number | null;
  actor_email: string;
  /** CUSTOMER, VENDOR, ADMINISTRATOR, RIDER, SYSTEM, or "" for an anonymous caller. */
  actor_role: string;
  /** `<area>.<verb>`, e.g. `shop.approved`. */
  action: string;
  action_label: string;
  target_type: string;
  target_id: string;
  target_repr: string;
  metadata: Record<string, unknown>;
  ip_address: string | null;
  user_agent: string;
};

/** `action` is an exact action or an area prefix ending in "." (e.g. "shop."). */
export async function listAdminAuditEvents(
  options: DateRange & { page?: number; action?: string; actor?: string; actorRole?: string } = {},
): Promise<PaginatedResponse<AuditEvent>> {
  const params = dateRangeQuery(options);
  params.set("page", String(options.page ?? 1));
  if (options.action) params.set("action", options.action);
  if (options.actor) params.set("actor", options.actor);
  if (options.actorRole) params.set("actor_role", options.actorRole);
  return apiFetch<PaginatedResponse<AuditEvent>>(withQuery("/api/admin/audit-events", params));
}

export type AdminOrderLine = PayoutLine & {
  shop: { id: number; name: string };
  payout: { id: number; status: PayoutStatus } | null;
};

export type AdminOrderDetail = ShippingDetails &
  OrderTotals & {
    id: number;
    placed_at: string;
    status: string;
    customer: OrderBuyer;
    commission_total: string;
    payment: {
      method: string;
      status: string;
      amount: string;
      transaction_reference: string;
      created_at: string;
      provider_reference: string;
      provider: string;
      msisdn: string;
      failure_reason: string;
      settled_by: string | null;
      settled_at: string | null;
    } | null;
    items: AdminOrderLine[];
    deliveries: DeliveryLeg[];
  };

export async function getAdminOrder(orderId: number | string): Promise<AdminOrderDetail> {
  return apiFetch<AdminOrderDetail>(`/api/admin/orders/${orderId}`);
}

/** Settle a cash-on-delivery or Lipa Namba payment by hand: `confirm` once the money is in,
 * `reject` (with a reason) if it never arrives — rejecting cancels the order. */
export async function settleOrderPayment(
  orderId: number | string,
  action: "confirm" | "reject",
  reason = "",
): Promise<AdminOrderDetail> {
  return apiFetch<AdminOrderDetail>(`/api/admin/orders/${orderId}/payment/${action}`, {
    method: "POST",
    body: JSON.stringify(reason ? { reason } : {}),
  });
}

export type AdminProduct = {
  id: number;
  name: string;
  shop: { id: number; name: string; status: string };
  category: string | null;
  price: string | null;
  stock_quantity: number | null;
  is_published: boolean;
  is_deleted: boolean;
  created_at: string;
  units_sold: number;
  revenue: string;
};

export async function listAdminProducts(
  options: { page?: number; shop?: number | string; search?: string; published?: boolean } = {},
): Promise<PaginatedResponse<AdminProduct>> {
  const params = new URLSearchParams({ page: String(options.page ?? 1) });
  if (options.shop) params.set("shop", String(options.shop));
  if (options.search) params.set("search", options.search);
  if (options.published !== undefined) params.set("published", String(options.published));
  return apiFetch<PaginatedResponse<AdminProduct>>(withQuery("/api/admin/products", params));
}

export type PayoutNetwork = "MPESA" | "TIGOPESA" | "AIRTEL" | "HALOPESA";

export type PayoutDetails = {
  payout_network: PayoutNetwork | "";
  payout_phone: string;
  payout_account_name: string;
};

export type VendorShopEarnings = BalanceFigures & {
  shop_id: number;
  shop_name: string;
  commission_rate: string;
  has_payout_details: boolean;
  payout_network: PayoutNetwork | "";
  payout_phone: string;
  payout_account_name: string;
};

export async function getVendorEarnings(): Promise<VendorShopEarnings[]> {
  return apiFetch<VendorShopEarnings[]>("/api/vendor/earnings");
}

/** PDF of the vendor's earnings per shop and every payout received. */
export async function downloadEarningsReport(): Promise<Blob> {
  return apiFetchBlob("/api/vendor/earnings/report.pdf");
}

export async function updatePayoutDetails(
  shopId: number | string,
  details: PayoutDetails,
): Promise<PayoutDetails> {
  return apiFetch<PayoutDetails>(`/api/vendor/shops/${shopId}/payout-details`, {
    method: "PATCH",
    body: JSON.stringify(details),
  });
}

export async function listVendorPayouts(page = 1): Promise<PaginatedResponse<Payout>> {
  return apiFetch<PaginatedResponse<Payout>>(`/api/vendor/payouts?page=${page}`);
}
