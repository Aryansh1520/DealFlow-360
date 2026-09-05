"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Bell } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useLiveNotifications } from "@/features/notifications/use-live-notifications";

function timeAgo(iso: string): string {
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 1000));
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

/**
 * Header bell — a live, actionable feed of quotation lifecycle events across the
 * org. The rep submits a quote, leaves it, and any later movement (approved,
 * countered, confirmed, …) shows up here; clicking a row opens that quote.
 */
export function NotificationBell() {
  const router = useRouter();
  const { enabled, items, unreadCount, markAllRead, clear, open } = useLiveNotifications();
  const [menuOpen, setMenuOpen] = React.useState(false);

  if (!enabled) return null;

  return (
    <DropdownMenu
      open={menuOpen}
      onOpenChange={(next) => {
        setMenuOpen(next);
        if (next) markAllRead();
      }}
    >
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="relative rounded-full"
          aria-label={unreadCount > 0 ? `${unreadCount} new notifications` : "Notifications"}
        >
          <Bell className="h-5 w-5" />
          {unreadCount > 0 && (
            <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-1 text-[10px] font-semibold leading-none text-primary-foreground">
              {unreadCount > 9 ? "9+" : unreadCount}
            </span>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80 p-0">
        <div className="flex items-center justify-between border-b px-3 py-2">
          <span className="text-sm font-semibold">Notifications</span>
          {items.length > 0 && (
            <button
              type="button"
              onClick={clear}
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              Clear all
            </button>
          )}
        </div>

        {items.length === 0 ? (
          <p className="px-3 py-8 text-center text-sm text-muted-foreground">
            You&apos;re all caught up.
          </p>
        ) : (
          <ul className="max-h-96 overflow-y-auto py-1">
            {items.map((n) => (
              <li key={n.id}>
                <button
                  type="button"
                  className={cn(
                    "flex w-full flex-col gap-0.5 px-3 py-2 text-left transition-colors hover:bg-accent",
                    !n.read && "bg-primary/5"
                  )}
                  onClick={() => {
                    open(n);
                    setMenuOpen(false);
                    if (n.quotationId != null) {
                      router.push(`/workspace/quotations/${n.quotationId}`);
                    }
                  }}
                >
                  <span className="text-sm leading-snug">{n.title}</span>
                  <span className="text-xs text-muted-foreground">{timeAgo(n.at)}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
