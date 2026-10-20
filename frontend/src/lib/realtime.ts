"use client";

/**
 * The live-update socket (`/ws/` on the API, served by `apps.realtime`). One connection per tab,
 * opened while some component listens and closed when the last one stops.
 *
 * The server sends hints only, e.g. `{"type": "order.updated", "order_id": 42}`, never order
 * data: a listener reacts by refetching through the REST API, which keeps every permission
 * check there. A missed hint just means the page catches up on its next fetch.
 */

import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";
import {
  API_BASE_URL,
  getAccessToken,
  onAccessTokenChange,
  refreshAccessToken,
} from "@/lib/api-client";

type OrderEventType = "order.created" | "order.updated" | "payment.updated" | "delivery.assigned";

export type RealtimeEventType = OrderEventType | "shop.updated";

/** `shop.updated` goes to a shop's owner (and the administrators) when it is approved or
 * rejected, so a vendor's open tabs see their shop go live without a reload. */
export type RealtimeEvent =
  { type: OrderEventType; order_id: number } | { type: "shop.updated"; shop_id: number };

/** One order to hear about: a signed-in buyer's by id, a guest's by its private token. */
export type RealtimeWatch = { orderId: number | string } | { guestToken: string };

type Listener = (event: RealtimeEvent) => void;
type SubscribeMessage = { order_id: number } | { guest_token: string };

const EVENT_TYPES = new Set<string>([
  "order.created",
  "order.updated",
  "payment.updated",
  "delivery.assigned",
  "shop.updated",
]);
const MAX_BACKOFF_MS = 30_000;
// The server closes with this when a different account authenticates on an open socket.
const CLOSE_ACCOUNT_CHANGED = 4409;

export function realtimeUrl(base = API_BASE_URL): string {
  return `${base.replace(/^http/, "ws").replace(/\/+$/, "")}/ws/`;
}

function subscribeMessage(watch: RealtimeWatch): SubscribeMessage | null {
  if ("guestToken" in watch) return watch.guestToken ? { guest_token: watch.guestToken } : null;
  const orderId = Number(watch.orderId);
  return Number.isInteger(orderId) && orderId > 0 ? { order_id: orderId } : null;
}

function isRealtimeEvent(message: unknown): message is RealtimeEvent {
  return (
    !!message &&
    typeof message === "object" &&
    EVENT_TYPES.has((message as { type?: unknown }).type as string)
  );
}

/** The connection, as a plain class so tests can drive it with a fake WebSocket. */
export class RealtimeConnection {
  private socket: WebSocket | null = null;
  private listeners = new Set<Listener>();
  // Subscriptions by their JSON, reference-counted: two components may watch the same order.
  private subscriptions = new Map<string, number>();
  private connected = false;
  private connectedListeners = new Set<() => void>();
  private attempts = 0;
  private retryTimer: ReturnType<typeof setTimeout> | null = null;
  private authRetried = false;
  private stopTokenWatch: (() => void) | null = null;

  constructor(
    private readonly url: string = realtimeUrl(),
    private readonly createSocket: (url: string) => WebSocket = (url) => new WebSocket(url),
  ) {}

  isConnected(): boolean {
    return this.connected;
  }

  onConnectedChange(callback: () => void): () => void {
    this.connectedListeners.add(callback);
    return () => {
      this.connectedListeners.delete(callback);
    };
  }

  listen(listener: Listener, watch?: RealtimeWatch): () => void {
    const message = watch ? subscribeMessage(watch) : null;
    const key = message ? JSON.stringify(message) : null;

    this.listeners.add(listener);
    if (key) {
      const count = this.subscriptions.get(key) ?? 0;
      this.subscriptions.set(key, count + 1);
      if (count === 0 && this.connected) this.send({ type: "subscribe", ...message });
    }
    this.start();

    return () => {
      this.listeners.delete(listener);
      if (key) {
        const count = (this.subscriptions.get(key) ?? 1) - 1;
        if (count > 0) {
          this.subscriptions.set(key, count);
        } else {
          this.subscriptions.delete(key);
          if (this.connected) this.send({ type: "unsubscribe", ...message });
        }
      }
      if (this.listeners.size === 0) this.stop();
    };
  }

  /** Reconnects straight away if the socket dropped (e.g. when the tab becomes visible). */
  wake(): void {
    if (this.listeners.size > 0 && !this.socket) {
      this.attempts = 0;
      this.connect();
    }
  }

  private start(): void {
    if (this.socket || this.retryTimer) return;
    this.stopTokenWatch ??= onAccessTokenChange((token) => this.onTokenChange(token));
    this.connect();
  }

  private stop(): void {
    this.stopTokenWatch?.();
    this.stopTokenWatch = null;
    if (this.retryTimer) clearTimeout(this.retryTimer);
    this.retryTimer = null;
    const socket = this.socket;
    this.socket = null;
    this.setConnected(false);
    socket?.close();
  }

  private connect(): void {
    if (this.retryTimer) clearTimeout(this.retryTimer);
    this.retryTimer = null;

    let socket: WebSocket;
    try {
      socket = this.createSocket(this.url);
    } catch {
      this.scheduleReconnect();
      return;
    }
    this.socket = socket;
    this.authRetried = false;

    socket.onopen = () => {
      if (this.socket !== socket) return;
      this.attempts = 0;
      const token = getAccessToken();
      if (token) {
        // Subscriptions wait for the answer: an order watched by id needs the account first.
        this.send({ type: "auth", token });
      } else {
        this.ready();
      }
    };
    socket.onmessage = (message) => {
      if (this.socket !== socket) return;
      this.onMessage(message.data);
    };
    socket.onclose = (event) => {
      if (this.socket !== socket) return;
      this.socket = null;
      this.setConnected(false);
      if (this.listeners.size === 0) return;
      if (event.code === CLOSE_ACCOUNT_CHANGED) {
        this.connect();
      } else {
        this.scheduleReconnect();
      }
    };
  }

  private onMessage(raw: unknown): void {
    let message: unknown;
    try {
      message = JSON.parse(String(raw));
    } catch {
      return;
    }
    const type = (message as { type?: unknown } | null)?.type;
    if (type === "auth.ok") {
      this.ready();
    } else if (type === "auth.error") {
      if (!this.authRetried) {
        // Most likely an expired access token: a refresh fires onTokenChange, which re-sends
        // auth. Without a session the socket still serves guest subscriptions.
        this.authRetried = true;
        void refreshAccessToken().then((token) => {
          if (!token) this.ready();
        });
      } else {
        this.ready();
      }
    } else if (isRealtimeEvent(message)) {
      this.listeners.forEach((listener) => listener(message));
    }
  }

  /** (Re)sends every subscription: an order watched by id may have been refused before the
   * account was known (e.g. signing in with the page open). The server ignores repeats. */
  private ready(): void {
    for (const key of this.subscriptions.keys()) {
      this.send({ type: "subscribe", ...JSON.parse(key) });
    }
    this.setConnected(true);
  }

  private onTokenChange(token: string | null): void {
    if (!this.socket) return;
    if (token) {
      if (this.socket.readyState === 1) this.send({ type: "auth", token });
    } else {
      // Signed out: start a fresh, anonymous socket rather than keep the old account's groups.
      const socket = this.socket;
      this.socket = null;
      this.setConnected(false);
      socket.close();
      this.connect();
    }
  }

  private scheduleReconnect(): void {
    if (this.listeners.size === 0 || this.retryTimer) return;
    const delay = Math.min(MAX_BACKOFF_MS, 1000 * 2 ** this.attempts);
    this.attempts += 1;
    // Jitter, so every open tab doesn't reconnect at the same instant after a deploy.
    this.retryTimer = setTimeout(() => this.connect(), delay / 2 + Math.random() * (delay / 2));
  }

  private send(message: object): void {
    if (this.socket?.readyState === 1) this.socket.send(JSON.stringify(message));
  }

  private setConnected(connected: boolean): void {
    if (this.connected === connected) return;
    this.connected = connected;
    this.connectedListeners.forEach((callback) => callback());
  }
}

let shared: RealtimeConnection | null = null;

function connection(): RealtimeConnection | null {
  if (typeof window === "undefined" || typeof WebSocket === "undefined") return null;
  if (!shared) {
    const created = new RealtimeConnection();
    shared = created;
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible") created.wake();
    });
  }
  return shared;
}

/**
 * Calls `onEvent` for live updates while mounted and `enabled`. Signed-in vendors, riders and
 * administrators hear about their own orders automatically; pass `watch` to also hear about one
 * order (a buyer's, by id, or a guest's, by token).
 */
export function useRealtime(
  onEvent: Listener,
  { enabled = true, watch }: { enabled?: boolean; watch?: RealtimeWatch } = {},
): void {
  const onEventRef = useRef(onEvent);
  useEffect(() => {
    onEventRef.current = onEvent;
  });

  const watchKey = watch ? JSON.stringify(watch) : "";
  useEffect(() => {
    if (!enabled) return;
    const conn = connection();
    if (!conn) return;
    const parsed = watchKey ? (JSON.parse(watchKey) as RealtimeWatch) : undefined;
    return conn.listen((event) => onEventRef.current(event), parsed);
  }, [enabled, watchKey]);
}

/**
 * For a page that fetches in an effect: `version` changes on every live update of one of `types`
 * (add it to the effect's deps), and `takeQuiet()` tells the effect whether this run is such a
 * refresh, which should keep the current data on screen rather than show a spinner or an error.
 */
export function useLiveRefresh(
  types: RealtimeEventType[],
  { enabled = true, watch }: { enabled?: boolean; watch?: RealtimeWatch } = {},
): { version: number; takeQuiet: () => boolean } {
  const [version, setVersion] = useState(0);
  const quiet = useRef(false);
  const typesKey = types.join(",");

  useRealtime(
    (event) => {
      if (typesKey.split(",").includes(event.type)) {
        quiet.current = true;
        setVersion((v) => v + 1);
      }
    },
    { enabled, watch },
  );

  const takeQuiet = useCallback(() => {
    const wasQuiet = quiet.current;
    quiet.current = false;
    return wasQuiet;
  }, []);

  return { version, takeQuiet };
}

/** Whether the live-update socket is up, so callers can poll less while it is. */
export function useRealtimeConnected(): boolean {
  return useSyncExternalStore(
    (callback) => connection()?.onConnectedChange(callback) ?? (() => {}),
    () => connection()?.isConnected() ?? false,
    () => false,
  );
}
