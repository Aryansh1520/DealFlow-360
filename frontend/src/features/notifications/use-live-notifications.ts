"use client";

import * as React from "react";
import { useQueryClient } from "@tanstack/react-query";

import type { StreamFrame } from "@/lib/api/types";
import { useLiveEvents } from "@/lib/live/use-live-events";
import { useAuth } from "@/features/auth/auth-context";

export interface LiveNotification {
  id: string;
  quotationId: number | null;
  eventType: string;
  reference: string | null;
  status: string | null;
  title: string;
  at: string;
  read: boolean;
}

/**
 * Lifecycle events worth interrupting a rep for. Routine builder edits
 * (`quote.line_*`, `quote.discount_changed`, `quote.customer_viewed`,
 * upsell add/dismiss, fulfilment internals) are intentionally excluded so the
 * bell stays signal, not noise.
 */
const NOTIFY: Record<string, (ref: string) => string> = {
  "quote.submitted": (r) => `${r} was submitted for approval`,
  "quote.approved": (r) => `${r} was approved`,
  "quote.rejected": (r) => `${r} was rejected`,
  "quote.returned": (r) => `${r} was returned for revision`,
  "quote.sent": (r) => `${r} was sent to the customer`,
  "quote.customer_countered": (r) => `${r} — customer asked for a different discount`,
  "quote.customer_commented": (r) => `${r} — customer left a comment`,
  "quote.customer_confirmed": (r) => `${r} was confirmed by the customer`,
  "quote.invoiced": (r) => `${r} was invoiced`,
  "quote.payment_recorded": (r) => `${r} — payment recorded`,
  "quote.cancelled": (r) => `${r} was cancelled`,
};

const MAX_ITEMS = 30;
const BURST_WINDOW_MS = 4000;

/**
 * Org-wide live notification feed for internal users. Subscribes to the
 * `approvals` bus scope (separate from the header `LiveIndicator`'s `dashboard`
 * subscription, so neither starves the other's per-scope queue budget) and turns
 * lifecycle frames into a readable, actionable list. State is in-memory — a
 * refresh clears it, which is fine for a session-length tool.
 */
export function useLiveNotifications() {
  const { hasPermission } = useAuth();
  const queryClient = useQueryClient();
  const [items, setItems] = React.useState<LiveNotification[]>([]);

  const scope = hasPermission("quotations:read") ? "approvals" : null;

  const { connected } = useLiveEvents(scope, (frame: StreamFrame) => {
    const make = NOTIFY[frame.event_type];
    if (!make) return;

    const reference = (frame.payload?.reference as string | undefined) ?? null;
    const status = (frame.payload?.status as string | undefined) ?? null;

    setItems((prev) => {
      const last = prev[0];
      if (
        last &&
        last.quotationId === frame.quotation_id &&
        last.eventType === frame.event_type &&
        Date.now() - new Date(last.at).getTime() < BURST_WINDOW_MS
      ) {
        return prev; // collapse a rapid burst of the same event on the same quote
      }
      const label = reference ?? `Quotation #${frame.quotation_id ?? "?"}`;
      const next: LiveNotification = {
        id: frame.id,
        quotationId: frame.quotation_id,
        eventType: frame.event_type,
        reference,
        status,
        title: make(label),
        at: frame.emitted_at ?? new Date().toISOString(),
        read: false,
      };
      return [next, ...prev].slice(0, MAX_ITEMS);
    });
  });

  const unreadCount = items.reduce((n, i) => n + (i.read ? 0 : 1), 0);

  const markAllRead = React.useCallback(
    () => setItems((prev) => (prev.some((i) => !i.read) ? prev.map((i) => ({ ...i, read: true })) : prev)),
    []
  );

  const clear = React.useCallback(() => setItems([]), []);

  /** Mark one read and pull the freshest copy of that quote so the screen the
   * rep lands on is already current. */
  const open = React.useCallback(
    (n: LiveNotification) => {
      setItems((prev) => prev.map((i) => (i.id === n.id ? { ...i, read: true } : i)));
      if (n.quotationId != null) {
        queryClient.invalidateQueries({ queryKey: ["quotations", n.quotationId], refetchType: "all" });
      }
    },
    [queryClient]
  );

  return { enabled: scope != null, connected, items, unreadCount, markAllRead, clear, open };
}
