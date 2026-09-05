"use client";

import * as React from "react";
import Link from "next/link";
import { ChevronRight } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Money } from "@/components/ui/money";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import type { PortalQuotationRead } from "@/lib/api/types";
import { usePortalQuotations } from "@/features/portal/hooks";

const STATUS_COPY: Record<string, string> = {
  sent: "Awaiting your review",
  under_negotiation: "Under negotiation",
  approved: "Ready to confirm",
  pending_l1: "With our team",
  pending_l2: "With our team",
  confirmed: "Confirmed",
  fulfilling: "In preparation",
  invoiced: "Invoiced",
  paid: "Paid",
  expired: "Expired",
  cancelled: "Cancelled",
};

// Quotes the customer can still act on — shown first, prominently.
const ACTIVE = new Set([
  "approved",
  "sent",
  "under_negotiation",
  "pending_l1",
  "pending_l2",
]);

export function PortalQuotationList() {
  const { data, isLoading } = usePortalQuotations({ page: 1, page_size: 100 });

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  const items = data?.items ?? [];
  const active = items.filter((q) => ACTIVE.has(q.status));
  const past = items.filter((q) => !ACTIVE.has(q.status));

  if (items.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Nothing here yet</CardTitle>
          <CardDescription>
            When your sales rep sends you a quotation, it will appear here for you to review.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <div className="space-y-8">
      <section>
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Needs your attention
        </h2>
        {active.length === 0 ? (
          <p className="rounded-md border p-4 text-sm text-muted-foreground">
            Nothing waiting on you right now.
          </p>
        ) : (
          <div className="space-y-3">
            {active.map((quote) => (
              <QuoteRow key={quote.id} quote={quote} highlight />
            ))}
          </div>
        )}
      </section>

      {past.length > 0 && (
        <PastQuotations quotes={past} />
      )}
    </div>
  );
}

function PastQuotations({ quotes }: { quotes: PortalQuotationRead[] }) {
  const [open, setOpen] = React.useState(quotes.length <= 5);
  const shown = open ? quotes : quotes.slice(0, 5);
  return (
    <section>
      <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
        Earlier quotations ({quotes.length})
      </h2>
      <div className="space-y-3">
        {shown.map((quote) => (
          <QuoteRow key={quote.id} quote={quote} />
        ))}
      </div>
      {!open && quotes.length > 5 && (
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="mt-3 text-sm text-primary hover:underline"
        >
          Show all {quotes.length}
        </button>
      )}
    </section>
  );
}

function QuoteRow({ quote, highlight }: { quote: PortalQuotationRead; highlight?: boolean }) {
  return (
    <Link href={`/portal/quotations/${quote.id}`} className="block">
      <Card
        className={cn(
          "transition-colors hover:border-primary/40",
          highlight && "border-primary/30 bg-primary/[0.02]"
        )}
      >
        <CardContent className="flex items-center justify-between p-5">
          <div>
            <p className="font-medium">Quotation {quote.reference}</p>
            <p className="text-sm text-muted-foreground">
              {quote.lines.length} item{quote.lines.length === 1 ? "" : "s"} ·{" "}
              <span className={cn(highlight && "font-medium text-foreground")}>
                {STATUS_COPY[quote.status] ?? quote.status}
              </span>
            </p>
          </div>
          <div className="flex items-center gap-4">
            <Money
              className="font-semibold"
              minor={quote.totals.total_minor}
              currency={quote.currency}
            />
            <ChevronRight className="h-5 w-5 text-muted-foreground" />
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
