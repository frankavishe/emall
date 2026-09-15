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
  if (!headers.has("Content-Type") && options.body) {
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
