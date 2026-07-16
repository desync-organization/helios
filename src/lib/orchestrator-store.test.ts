import { afterEach, beforeEach, describe, expect, it } from "bun:test";

import {
  appendCostSummary,
  type CostSummary,
  useOrchestratorStore,
} from "./orchestrator-store";

type SocketListener = EventListenerOrEventListenerObject;

class FakeWebSocket {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;
  static instances: FakeWebSocket[] = [];

  readonly sent: string[] = [];
  readyState = FakeWebSocket.CONNECTING;
  private readonly listeners = new Map<string, SocketListener[]>();

  constructor(readonly url: string) {
    FakeWebSocket.instances.push(this);
  }

  addEventListener(type: string, listener: SocketListener) {
    const listeners = this.listeners.get(type) ?? [];
    listeners.push(listener);
    this.listeners.set(type, listeners);
  }

  send(data: string | ArrayBufferLike | Blob | ArrayBufferView) {
    if (this.readyState !== FakeWebSocket.OPEN) {
      throw new Error("socket is not open");
    }
    this.sent.push(String(data));
  }

  close() {
    this.readyState = FakeWebSocket.CLOSED;
    this.dispatch("close");
  }

  open() {
    this.readyState = FakeWebSocket.OPEN;
    this.dispatch("open");
  }

  beginClosing() {
    this.readyState = FakeWebSocket.CLOSING;
  }

  finishRemoteClose() {
    this.readyState = FakeWebSocket.CLOSED;
    this.dispatch("close");
  }

  private dispatch(type: string) {
    const event = { type } as Event;
    for (const listener of this.listeners.get(type) ?? []) {
      if (typeof listener === "function") {
        listener.call(this as unknown as WebSocket, event);
      } else {
        listener.handleEvent(event);
      }
    }
  }
}

const nativeWebSocket = globalThis.WebSocket;

beforeEach(() => {
  globalThis.WebSocket = FakeWebSocket as unknown as typeof WebSocket;
  FakeWebSocket.instances = [];
  useOrchestratorStore.getState().disconnect();
});

afterEach(() => {
  useOrchestratorStore.getState().disconnect();
  globalThis.WebSocket = nativeWebSocket;
});

describe("orchestrator WebSocket lifecycle", () => {
  it("flushes a pre-open prompt exactly once", () => {
    const store = useOrchestratorStore.getState();
    store.connect("ws://127.0.0.1:8788/ws");
    store.sendChatMessage("Build a bakery site");

    const socket = FakeWebSocket.instances[0];
    expect(socket.sent).toEqual([]);

    socket.open();
    socket.open();

    expect(socket.sent).toEqual([
      JSON.stringify({ type: "prompt", data: "Build a bakery site" }),
    ]);
  });

  it("ignores a stale socket closing after its replacement opens", () => {
    const store = useOrchestratorStore.getState();
    store.connect("ws://127.0.0.1:8788/ws");
    const staleSocket = FakeWebSocket.instances[0];
    staleSocket.open();
    staleSocket.beginClosing();

    useOrchestratorStore.getState().connect("ws://127.0.0.1:8788/ws");
    const currentSocket = FakeWebSocket.instances[1];
    currentSocket.open();
    staleSocket.finishRemoteClose();

    expect(useOrchestratorStore.getState().connected).toBe(true);
    useOrchestratorStore.getState().sendChatMessage("Build a docs site");
    expect(currentSocket.sent).toEqual([
      JSON.stringify({ type: "prompt", data: "Build a docs site" }),
    ]);
  });

  it("does not reconnect after an explicit disconnect", () => {
    const store = useOrchestratorStore.getState();
    store.connect("ws://127.0.0.1:8788/ws");
    const socket = FakeWebSocket.instances[0];
    socket.open();
    store.disconnect();

    expect(useOrchestratorStore.getState().connected).toBe(false);
    expect(FakeWebSocket.instances).toHaveLength(1);
  });
});

describe("appendCostSummary", () => {
  it("updates totals and one office without mutating the prior summary", () => {
    const empty: CostSummary = {
      totalInputTokens: 0,
      totalOutputTokens: 0,
      totalCostUsd: 0,
      totalCalls: 0,
      perOffice: [],
    };
    const first = appendCostSummary(empty, {
      office: "CEO OFFICE",
      input_tokens: 10,
      output_tokens: 4,
      cost_usd: 0.002,
      latency_s: 0.5,
      timestamp: 1,
    });
    const second = appendCostSummary(first, {
      office: "CEO OFFICE-retry",
      input_tokens: 5,
      output_tokens: 2,
      cost_usd: 0.001,
      latency_s: 0.25,
      timestamp: 2,
    });

    expect(empty.totalCalls).toBe(0);
    expect(first.totalCalls).toBe(1);
    expect(second).toEqual({
      totalInputTokens: 15,
      totalOutputTokens: 6,
      totalCostUsd: 0.003,
      totalCalls: 2,
      perOffice: [{
        office: "CEO",
        calls: 2,
        inputTokens: 15,
        outputTokens: 6,
        costUsd: 0.003,
        totalLatency: 0.75,
      }],
    });
  });
});
