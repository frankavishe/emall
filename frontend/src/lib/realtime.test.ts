import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { setAccessToken } from "./api-client";
import { RealtimeConnection, realtimeUrl } from "./realtime";

class FakeSocket {
  static instances: FakeSocket[] = [];
  readyState = 0;
  sent: unknown[] = [];
  closed = false;
  onopen: (() => void) | null = null;
  onmessage: ((message: { data: string }) => void) | null = null;
  onclose: ((event: { code: number }) => void) | null = null;

  constructor(public url: string) {
    FakeSocket.instances.push(this);
  }

  send(data: string) {
    this.sent.push(JSON.parse(data));
  }

  close() {
    this.closed = true;
    this.readyState = 3;
  }

  // Test helpers: what the server would do.
  open() {
    this.readyState = 1;
    this.onopen?.();
  }

  receive(message: object) {
    this.onmessage?.({ data: JSON.stringify(message) });
  }

  drop(code = 1006) {
    this.readyState = 3;
    this.onclose?.({ code });
  }
}

function latest(): FakeSocket {
  return FakeSocket.instances[FakeSocket.instances.length - 1];
}

// Every listener a test starts, stopped afterwards so its connection stops reacting to the
// (module-wide) access token.
let stops: (() => void)[] = [];

function makeConnection() {
  const conn = new RealtimeConnection(
    "ws://api.test/ws/",
    (url) => new FakeSocket(url) as unknown as WebSocket,
  );
  const listen = conn.listen.bind(conn);
  conn.listen = (...args) => {
    const stop = listen(...args);
    stops.push(stop);
    return stop;
  };
  return conn;
}

beforeEach(() => {
  FakeSocket.instances = [];
  setAccessToken(null);
  vi.useFakeTimers();
});

afterEach(() => {
  stops.forEach((stop) => stop());
  stops = [];
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("realtimeUrl", () => {
  it("turns the API base into a ws(s) URL", () => {
    expect(realtimeUrl("https://api.mangimall.com")).toBe("wss://api.mangimall.com/ws/");
    expect(realtimeUrl("http://localhost:8000/")).toBe("ws://localhost:8000/ws/");
  });
});

describe("RealtimeConnection", () => {
  it("connects on the first listener and closes after the last", () => {
    const conn = makeConnection();
    const stopA = conn.listen(() => {});
    const stopB = conn.listen(() => {});
    expect(FakeSocket.instances).toHaveLength(1);

    stopA();
    expect(latest().closed).toBe(false);
    stopB();
    expect(latest().closed).toBe(true);
  });

  it("subscribes a guest straight away when there's no session", () => {
    const conn = makeConnection();
    conn.listen(() => {}, { guestToken: "secret" });
    latest().open();

    expect(latest().sent).toEqual([{ type: "subscribe", guest_token: "secret" }]);
    expect(conn.isConnected()).toBe(true);
  });

  it("authenticates first and subscribes once the account is known", () => {
    setAccessToken("access-1");
    const conn = makeConnection();
    conn.listen(() => {}, { orderId: "42" });
    latest().open();
    expect(latest().sent).toEqual([{ type: "auth", token: "access-1" }]);

    latest().receive({ type: "auth.ok" });
    expect(latest().sent).toEqual([
      { type: "auth", token: "access-1" },
      { type: "subscribe", order_id: 42 },
    ]);
  });

  it("refreshes an expired token and re-authenticates", async () => {
    setAccessToken("expired");
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({ access: "fresh" }), { status: 200 })),
    );
    const conn = makeConnection();
    conn.listen(() => {});
    latest().open();

    latest().receive({ type: "auth.error" });
    await vi.waitFor(() =>
      expect(latest().sent).toContainEqual({ type: "auth", token: "fresh" }),
    );
  });

  it("passes events to listeners and ignores replies", () => {
    const conn = makeConnection();
    const events: unknown[] = [];
    conn.listen((event) => events.push(event));
    latest().open();

    latest().receive({ type: "subscribed", order_id: 1 });
    latest().receive({ type: "order.updated", order_id: 1 });
    expect(events).toEqual([{ type: "order.updated", order_id: 1 }]);
  });

  it("shares one subscription between listeners of the same order", () => {
    const conn = makeConnection();
    const stopA = conn.listen(() => {}, { guestToken: "t" });
    latest().open();
    const stopB = conn.listen(() => {}, { guestToken: "t" });
    const stopC = conn.listen(() => {});

    stopA();
    expect(latest().sent).toEqual([{ type: "subscribe", guest_token: "t" }]);
    stopB();
    expect(latest().sent).toContainEqual({ type: "unsubscribe", guest_token: "t" });
    stopC();
  });

  it("reconnects with backoff and re-subscribes", () => {
    const conn = makeConnection();
    conn.listen(() => {}, { guestToken: "t" });
    latest().open();

    latest().drop();
    expect(conn.isConnected()).toBe(false);
    expect(FakeSocket.instances).toHaveLength(1);

    vi.advanceTimersByTime(1000);
    expect(FakeSocket.instances).toHaveLength(2);

    // A second failure in a row waits longer: 2s, less up to half of it for jitter.
    latest().drop();
    vi.advanceTimersByTime(900);
    expect(FakeSocket.instances).toHaveLength(2);
    vi.advanceTimersByTime(1100);
    expect(FakeSocket.instances).toHaveLength(3);

    latest().open();
    expect(latest().sent).toEqual([{ type: "subscribe", guest_token: "t" }]);
  });

  it("starts an anonymous socket on sign-out", () => {
    setAccessToken("access-1");
    const conn = makeConnection();
    conn.listen(() => {});
    const first = latest();
    first.open();

    setAccessToken(null);
    expect(first.closed).toBe(true);
    expect(FakeSocket.instances).toHaveLength(2);
  });

  it("re-authenticates on sign-in with the socket open", () => {
    const conn = makeConnection();
    conn.listen(() => {});
    latest().open();

    setAccessToken("access-2");
    expect(latest().sent).toEqual([{ type: "auth", token: "access-2" }]);
  });
});
