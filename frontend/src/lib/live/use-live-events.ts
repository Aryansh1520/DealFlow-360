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

export function useLiveEvents(
  scope: string | null,
  onFrame?: (frame: StreamFrame) => void
): { connected: boolean } {
  const { userType, isAuthenticated } = useAuth();
  const [connected, setConnected] = React.useState(false);
  const onFrameRef = React.useRef(onFrame);
  onFrameRef.current = onFrame;

  React.useEffect(() => {
    if (!scope || !isAuthenticated) return;

    let stopped = false;
    let controller: AbortController | null = null;
    let backoff = BACKOFF_START;
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;
    let heartbeatTimer: ReturnType<typeof setTimeout> | undefined;

    const armHeartbeatWatchdog = () => {
      if (heartbeatTimer) clearTimeout(heartbeatTimer);
      heartbeatTimer = setTimeout(() => {
        // Silence too long — force a reconnect.
        controller?.abort();
      }, HEARTBEAT_TIMEOUT);
    };

    const scheduleReconnect = () => {
      if (stopped) return;
      const jittered = backoff * (0.7 + Math.random() * 0.6);
      reconnectTimer = setTimeout(connect, jittered);
      backoff = Math.min(backoff * 2, BACKOFF_CAP);
    };

    const connect = async () => {
      if (stopped) return;
      controller = new AbortController();
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
            signal: controller.signal,
          }
        );
        if (!response.ok || !response.body) {
          throw new Error(`stream ${response.status}`);
        }

        setConnected(true);
        armHeartbeatWatchdog();

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (!stopped) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          // Frames are separated by a blank line.
          let sep: number;
          while ((sep = buffer.indexOf("\n\n")) !== -1) {
            const raw = buffer.slice(0, sep);
            buffer = buffer.slice(sep + 2);
            const dataLine = raw
              .split("\n")
              .find((line) => line.startsWith("data:"));
            if (!dataLine) continue;
            try {
              const frame = JSON.parse(dataLine.slice(5).trim()) as StreamFrame;
              backoff = BACKOFF_START; // a live frame resets the backoff
              armHeartbeatWatchdog();
              if (frame.event_type !== "heartbeat") {
                onFrameRef.current?.(frame);
              }
            } catch {
              /* ignore a partial / malformed frame */
            }
          }
        }
        throw new Error("stream ended");
      } catch (err) {
        if (stopped) return;
        setConnected(false);
        scheduleReconnect();
      }
    };

    connect();

    return () => {
      stopped = true;
      controller?.abort();
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (heartbeatTimer) clearTimeout(heartbeatTimer);
      setConnected(false);
    };
    // Reconnect from scratch when the scope or the principal changes.
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
