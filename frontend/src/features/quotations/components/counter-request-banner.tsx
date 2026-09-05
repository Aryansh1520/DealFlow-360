"use client";

import * as React from "react";
import { Check, Loader2, MessageSquareQuote, X } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { formatBps } from "@/lib/money";
import type { QuotationRead, QuoteEventRead } from "@/lib/api/types";
import { useAuth } from "@/features/auth/auth-context";
import { useQuotationEvents, useRejectCounter } from "@/features/quotations/hooks";

// Events that count as the rep having responded to the counter — once one of these
// lands after the counter, the banner is done.
const REP_RESPONSE = new Set([
  "quote.discount_changed",
  "quote.line_added",
  "quote.line_updated",
  "quote.line_removed",
  "quote.counter_rejected",
]);

/**
 * Surfaces the customer's most recent counter-offer as an action, not a buried
 * timeline line. `BACKEND_PHASE_3.md` Task 3: "the rep sees it in the timeline
 * and applies or rejects it — not auto-applied."
 *
 * "Review" does not write anything — it stages the requested discount into the
 * builder's Order-discount field (`onStageOrderDiscount`) for the rep to confirm
 * and commit themselves, which then runs through the golden-rule approval re-gate.
 * "Decline" records `quote.counter_rejected` so the customer is told.
 */
export function CounterRequestBanner({
  quotation,
  onStageOrderDiscount,
}: {
  quotation: QuotationRead;
  onStageOrderDiscount: (requestedBps: number) => void;
}) {
  const { hasPermission } = useAuth();
  const [dismissed, setDismissed] = React.useState(false);
  const { data } = useQuotationEvents(quotation.id);
  const reject = useRejectCounter(quotation.id);

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
          title="Hide for now"
          onClick={() => setDismissed(true)}
        >
          <X className="h-4 w-4" />
        </Button>
      </AlertTitle>
      <AlertDescription className="space-y-2">
        {message && <p className="italic">“{message}”</p>}
        <p className="text-xs text-muted-foreground">
          Nothing is applied automatically. Review it into the order-discount field to
          adjust and commit it yourself, or decline to keep the current terms — the
          customer is told either way.
        </p>
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            disabled={requestedBps <= 0}
            onClick={() => onStageOrderDiscount(requestedBps)}
          >
            <Check className="h-4 w-4" />
            Review {formatBps(requestedBps)} order discount
          </Button>
          <Button
            size="sm"
            variant="ghost"
            disabled={reject.isPending}
            onClick={() =>
              reject.mutate(
                { expected_version: quotation.version },
                { onSuccess: () => setDismissed(true) }
              )
            }
          >
            {reject.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Decline
          </Button>
        </div>
      </AlertDescription>
    </Alert>
  );
}
