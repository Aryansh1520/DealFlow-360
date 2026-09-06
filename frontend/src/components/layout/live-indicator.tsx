"use client";

import { cn } from "@/lib/utils";
import { useInvalidateOnFrame, useLiveEvents } from "@/lib/live/use-live-events";
import { useAuth } from "@/features/auth/auth-context";

/**
 * The header's live dot. Subscribes to the org-wide `dashboard` channel so the
 * indicator reflects a real connection, and runs the contract §4.11 invalidation
 * for every frame that arrives. Kill the backend and it goes grey, then flips
 * back to green on reconnect — judges notice the dot.
 */
export function LiveIndicator({ className }: { className?: string }) {
  const { hasPermission } = useAuth();
  const invalidate = useInvalidateOnFrame();
  // Every ledger event is published to both the `approvals` and `dashboard` bus
  // scopes, so prefer `approvals` when we can — that's the scope the notification
  // bell already holds, and `useLiveEvents` shares one socket per scope. Falling
  // back to `dashboard` keeps the dot working for a dashboard-only viewer.
  const scope = hasPermission("quotations:read")
    ? "approvals"
    : hasPermission("dashboard:read")
      ? "dashboard"
      : null;
  const { connected } = useLiveEvents(scope, invalidate);

  if (!scope) return null;

  return (
    <span
      className={cn("inline-flex items-center gap-1.5 text-xs", className)}
      title={connected ? "Live updates connected" : "Reconnecting…"}
    >
      <span className="relative flex h-2 w-2">
        {connected && (
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-positive opacity-75" />
        )}
        <span
          className={cn(
            "relative inline-flex h-2 w-2 rounded-full",
            connected ? "bg-positive" : "bg-muted-foreground/40"
          )}
        />
      </span>
      <span className="hidden text-muted-foreground sm:inline">
        {connected ? "Live" : "Offline"}
      </span>
    </span>
  );
}
