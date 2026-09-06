"use client";

import * as React from "react";
import { useQueryClient } from "@tanstack/react-query";

import { API_URL } from "@/lib/config";
import { tokenStorage } from "@/lib/api-client";
import type { StreamFrame } from "@/lib/api/types";
import { useAuth } from "@/features/auth/auth-context";

/**
 * `text/event-stream` client — `FRONTEND_PHASE_3.md` Task 1 / `API_CONTRACT.md` §4.11.
 *
 * Deliberately NOT `EventSource`: it cannot set an `Authorization` header. We use
 * `fetch` + `response.body.getReader()` and parse frames by hand.
 *
 * Reconnects with exponential backoff (1s → 2s → 4s, capped 15s) + jitter, resets
 * the backoff on any frame, and treats >60s of silence (no heartbeat) as a dead
 * connection.
 */
const BACKOFF_START = 1000;
const BACKOFF_CAP = 15000;
const HEARTBEAT_TIMEOUT = 60000;

/**
 * One live `fetch` SSE stream per scope, shared by every `useLiveEvents` consumer.
 *
 * A browser allows only ~6 concurrent connections per origin over HTTP/1.1, and an
 * SSE stream holds its slot for the whole session. Without sharing, each mounted
 * hook (header live dot, notification bell, a quote page, …) opened its own socket
 * and normal REST calls queued for tens of seconds behind them. Now N hooks on the
 * same scope cost exactly one socket; the stream tears down when the last consumer
 * unmounts.
 */
type FrameListener = (frame: StreamFrame) => void;
type StatusListener = (connected: boolean) => void;

interface ScopeChannel {
  frameListeners: Set<FrameListener>;
  statusListeners: Set<StatusListener>;
  connected: boolean;
  stopped: boolean;
  controller: AbortController | null;
  backoff: number;
  reconnectTimer: ReturnType<typeof setTimeout> | undefined;
  heartbeatTimer: ReturnType<typeof setTimeout> | undefined;
}

const channels = new Map<string, ScopeChannel>();

function openChannel(scope: string): ScopeChannel {
  const channel: ScopeChannel = {
    frameListeners: new Set(),
    statusListeners: new Set(),
    connected: false,
    stopped: false,
    controller: null,
    backoff: BACKOFF_START,
    reconnectTimer: undefined,
    heartbeatTimer: undefined,
  };
  channels.set(scope, channel);

  const setStatus = (value: boolean) => {
    channel.connected = value;
    for (const listener of channel.statusListeners) listener(value);
  };

  const armHeartbeatWatchdog = () => {
    if (channel.heartbeatTimer) clearTimeout(channel.heartbeatTimer);
    channel.heartbeatTimer = setTimeout(() => {
      // Silence too long — force a reconnect.
      channel.controller?.abort();
    }, HEARTBEAT_TIMEOUT);
  };

  const scheduleReconnect = () => {
    if (channel.stopped) return;
    const jittered = channel.backoff * (0.7 + Math.random() * 0.6);
    channel.reconnectTimer = setTimeout(connect, jittered);
    channel.backoff = Math.min(channel.backoff * 2, BACKOFF_CAP);
  };

  const connect = async () => {
    if (channel.stopped) return;
    channel.controller = new AbortController();
    const token = tokenStorage.getAccess();
    if (!token) {
      scheduleReconnect();
      return;
    }

    try {
      const response = await fetch(
        `${API_URL}/events/stream?scope=${encodeURIComponent(scope)}`,
        {
          headers: { Authorization: `Bearer ${token}`, Accept: "text/event-stream" },
          signal: channel.controller.signal,
        }
      );
      if (!response.ok || !response.body) {
        throw new Error(`stream ${response.status}`);
      }

      setStatus(true);
      armHeartbeatWatchdog();

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (!channel.stopped) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // Frames are separated by a blank line.
        let sep: number;
        while ((sep = buffer.indexOf("\n\n")) !== -1) {
          const raw = buffer.slice(0, sep);
          buffer = buffer.slice(sep + 2);
          const dataLine = raw.split("\n").find((line) => line.startsWith("data:"));
          if (!dataLine) continue;
          try {
            const frame = JSON.parse(dataLine.slice(5).trim()) as StreamFrame;
            channel.backoff = BACKOFF_START; // a live frame resets the backoff
            armHeartbeatWatchdog();
            if (frame.event_type !== "heartbeat") {
              for (const listener of channel.frameListeners) listener(frame);
            }
          } catch {
            /* ignore a partial / malformed frame */
          }
        }
      }
      throw new Error("stream ended");
    } catch {
      if (channel.stopped) return;
      setStatus(false);
      scheduleReconnect();
    }
  };

  connect();
  return channel;
}

function acquireChannel(
  scope: string,
  onFrame: FrameListener,
  onStatus: StatusListener
): ScopeChannel {
  const channel = channels.get(scope) ?? openChannel(scope);
  channel.frameListeners.add(onFrame);
  channel.statusListeners.add(onStatus);
  return channel;
}

function releaseChannel(scope: string, onFrame: FrameListener, onStatus: StatusListener): void {
  const channel = channels.get(scope);
  if (!channel) return;
  channel.frameListeners.delete(onFrame);
  channel.statusListeners.delete(onStatus);
  if (channel.frameListeners.size > 0 || channel.statusListeners.size > 0) return;

  // Last consumer gone — tear the stream down.
  channel.stopped = true;
  channel.controller?.abort();
  if (channel.reconnectTimer) clearTimeout(channel.reconnectTimer);
  if (channel.heartbeatTimer) clearTimeout(channel.heartbeatTimer);
  channels.delete(scope);
}

export function useLiveEvents(
  scope: string | null,
  onFrame?: (frame: StreamFrame) => void
): { connected: boolean } {
  const { userType, isAuthenticated } = useAuth();
  const [connected, setConnected] = React.useState(false);
  const onFrameRef = React.useRef(onFrame);
  onFrameRef.current = onFrame;

  React.useEffect(() => {
    if (!scope || !isAuthenticated) {
      setConnected(false);
      return;
    }

    const frameListener: FrameListener = (frame) => onFrameRef.current?.(frame);
    const statusListener: StatusListener = (value) => setConnected(value);

    const channel = acquireChannel(scope, frameListener, statusListener);
    setConnected(channel.connected);

    return () => releaseChannel(scope, frameListener, statusListener);
    // Re-acquire when the scope or the principal changes (a new token is read on
    // the next (re)connect).
  }, [scope, isAuthenticated, userType]);

  return { connected };
}

/**
 * The contract §4.11 invalidation rule, as a ready-made `onFrame`. Never patches
 * cache from `frame.payload` — the frame is a notification; the refetch goes
 * through the normal authorised endpoint.
 */
export function useInvalidateOnFrame(): (frame: StreamFrame) => void {
  const queryClient = useQueryClient();
  return React.useCallback(
    (frame: StreamFrame) => {
      if (frame.event_type === "heartbeat") return;
      if (frame.quotation_id != null) {
        // `refetchType: "all"` — re-pull even queries with no mounted observer
        // right now (a background tab, a collapsed panel). Without it the global
        // `staleTime` can leave a stale render on screen until the next window
        // focus. These keys are all scoped to one quotation, so the extra
        // fetches are cheap and bounded.
        const opts = { refetchType: "all" as const };
        queryClient.invalidateQueries({ queryKey: ["quotations", frame.quotation_id], ...opts });
        queryClient.invalidateQueries({
          queryKey: ["portal", "quotation", frame.quotation_id],
          ...opts,
        });
        queryClient.invalidateQueries({ queryKey: ["fulfillment", frame.quotation_id], ...opts });
        queryClient.invalidateQueries({ queryKey: ["billing", frame.quotation_id], ...opts });
      }
      // Keep whichever list is currently on screen fresh (the internal quotations
      // list / pipeline, or the customer's portal list) without forcing a refetch
      // of every cached detail.
      queryClient.invalidateQueries({ queryKey: ["quotations"], refetchType: "active" });
      queryClient.invalidateQueries({ queryKey: ["portal", "quotations"], refetchType: "active" });
      if (frame.scope === "approvals") {
        queryClient.invalidateQueries({ queryKey: ["approvals"] });
      }
      if (frame.scope === "dashboard") {
        queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      }
    },
    [queryClient]
  );
}
