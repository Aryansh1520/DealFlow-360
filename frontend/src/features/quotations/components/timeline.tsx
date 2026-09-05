"use client";

import * as React from "react";
import {
  Ban,
  CheckCircle2,
  ChevronDown,
  Clock,
  MessageSquare,
  Package,
  PlusCircle,
  Send,
  Sparkles,
  Truck,
  XCircle,
  type LucideIcon,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import type { QuoteEventRead } from "@/lib/api/types";
import { useQuotationEvents } from "@/features/quotations/hooks";

const EVENT_ICON: Record<string, LucideIcon> = {
  "quote.created": PlusCircle,
  "quote.line_added": PlusCircle,
  "quote.line_updated": PlusCircle,
  "quote.line_removed": XCircle,
  "quote.discount_changed": Clock,
  "quote.submitted": Send,
  "quote.approved": CheckCircle2,
  "quote.rejected": XCircle,
  "quote.returned": Ban,
  "quote.sent": Send,
  "quote.customer_viewed": MessageSquare,
  "quote.customer_commented": MessageSquare,
  "quote.customer_countered": MessageSquare,
  "quote.customer_confirmed": CheckCircle2,
  "quote.upsell_added": Sparkles,
  "quote.upsell_dismissed": Sparkles,
  "quote.fulfillment_planned": Package,
  "quote.fulfillment_overridden": Package,
  "quote.backorder_consolidated": Truck,
  "quote.invoiced": Package,
  "quote.payment_recorded": CheckCircle2,
  "quote.invoice_superseded": Clock,
  "quote.cancelled": Ban,
};

const EVENT_TONE: Record<string, string> = {
  "quote.approved": "text-positive",
  "quote.customer_confirmed": "text-positive",
  "quote.payment_recorded": "text-positive",
  "quote.rejected": "text-danger",
  "quote.cancelled": "text-danger",
  "quote.discount_changed": "text-warning",
  "quote.returned": "text-warning",
};

export function Timeline({ quotationId }: { quotationId: number }) {
  const { data, isLoading, hasNextPage, fetchNextPage, isFetchingNextPage } =
    useQuotationEvents(quotationId);

  const events = data?.pages.flatMap((page) => page.items) ?? [];

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 4 }).map((_, index) => (
          <Skeleton key={index} className="h-12 w-full" />
        ))}
      </div>
    );
  }

  if (events.length === 0) {
    return <p className="text-sm text-muted-foreground">No activity yet.</p>;
  }

  return (
    <div className="space-y-1">
      {events.map((event) => (
        <EventRow key={event.id} event={event} />
      ))}
      {hasNextPage && (
        <Button
          variant="ghost"
          size="sm"
          className="w-full"
          disabled={isFetchingNextPage}
          onClick={() => fetchNextPage()}
        >
          {isFetchingNextPage ? "Loading…" : "Load more"}
        </Button>
      )}
    </div>
  );
}

function EventRow({ event }: { event: QuoteEventRead }) {
  const [expanded, setExpanded] = React.useState(false);
  const Icon = EVENT_ICON[event.event_type] ?? Clock;
  const tone = EVENT_TONE[event.event_type] ?? "text-muted-foreground";
  const hasPayload = Object.keys(event.payload ?? {}).length > 0;

  return (
    <div className="flex gap-3 rounded-md px-2 py-2 hover:bg-accent/50">
      <Icon className={cn("mt-0.5 h-4 w-4 shrink-0", tone)} />
      <div className="min-w-0 flex-1">
        <p className="text-sm">{event.summary}</p>
        <div className="mt-0.5 flex items-center gap-2 text-xs text-muted-foreground">
          <span>{event.actor_name}</span>
          <Badge variant="outline" className="px-1.5 py-0 text-[10px] capitalize">
            {event.actor_type}
          </Badge>
          <span>{new Date(event.created_at).toLocaleString()}</span>
          {hasPayload && (
            <button
              type="button"
              onClick={() => setExpanded((prev) => !prev)}
              className="flex items-center gap-0.5 hover:text-foreground"
            >
              Details
              <ChevronDown className={cn("h-3 w-3 transition-transform", expanded && "rotate-180")} />
            </button>
          )}
        </div>
        {expanded && (
          <pre className="mt-1.5 max-h-40 overflow-auto rounded-md bg-muted p-2 text-[11px]">
            {JSON.stringify(event.payload, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
}
