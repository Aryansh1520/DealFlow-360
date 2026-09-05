"use client";

import * as React from "react";
import { Check, Loader2, MessageSquareQuote, X } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { formatBps } from "@/lib/money";
import type { QuotationRead, QuoteEventRead } from "@/lib/api/types";
import { useAuth } from "@/features/auth/auth-context";
import { useQuotationEvents, useUpdateQuotation } from "@/features/quotations/hooks";

// Events that count as the rep having responded to the counter.
const REP_RESPONSE = new Set([
  "quote.discount_changed",
  "quote.line_added",
  "quote.line_updated",
  "quote.line_removed",
]);

/**
 * Surfaces the customer's most recent counter-offer as an action, not a buried
 * timeline line. `BACKEND_PHASE_3.md` Task 3: "the rep sees it in the timeline
 * and applies or rejects it — not auto-applied."
 */
export function CounterRequestBanner({ quotation }: { quotation: QuotationRead }) {
  const { hasPermission } = useAuth();
  const [dismissed, setDismissed] = React.useState(false);
  const { data } = useQuotationEvents(quotation.id);
  const update = useUpdateQuotation(quotation.id);

  const events: QuoteEventRead[] = React.useMemo(
    () => (data?.pages ?? []).flatMap((p) => p.items),
    [data]
  );

  const counter = React.useMemo(() => {
    const c = events.find((e) => e.event_type === "quote.customer_countered");
    if (!c) return null;
    const respondedAfter = events.some(
      (e) => REP_RESPONSE.has(e.event_type) && e.created_at > c.created_at
    );
    return respondedAfter ? null : c;
  }, [events]);

  if (!counter || dismissed || !hasPermission("quotations:write")) return null;

  const requestedBps = Number(counter.payload?.requested_discount_bps ?? 0);
  const message = (counter.payload?.message as string | undefined) ?? null;
  const lineScoped = counter.payload?.line_id != null;

  return (
    <Alert variant="warning">
      <MessageSquareQuote className="h-4 w-4" />
      <AlertTitle className="flex items-center justify-between">
        <span>
          {counter.actor_name} requested a {formatBps(requestedBps)} discount
          {lineScoped ? " on one line" : ""}
        </span>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6"
          title="Dismiss"
          onClick={() => setDismissed(true)}
        >
          <X className="h-4 w-4" />
        </Button>
      </AlertTitle>
      <AlertDescription className="space-y-2">
        {message && <p className="italic">“{message}”</p>}
        <p className="text-xs text-muted-foreground">
          Not applied automatically. Apply it as an order-level discount, adjust a line
          yourself, or dismiss to leave the terms unchanged.
        </p>
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            disabled={update.isPending || requestedBps <= 0}
            onClick={() =>
              update.mutate(
                {
                  expected_version: quotation.version,
                  order_discount_bps: requestedBps,
                },
                { onSuccess: () => setDismissed(true) }
              )
            }
          >
            {update.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Check className="h-4 w-4" />
            )}
            Apply {formatBps(requestedBps)} order discount
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setDismissed(true)}>
            Dismiss
          </Button>
        </div>
      </AlertDescription>
    </Alert>
  );
}
