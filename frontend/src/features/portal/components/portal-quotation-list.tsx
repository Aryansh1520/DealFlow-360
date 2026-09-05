"use client";

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

const ACTIONABLE = new Set(["sent", "under_negotiation", "approved"]);

export function PortalQuotationList() {
  const { data, isLoading } = usePortalQuotations({ page: 1, page_size: 50 });

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  const items = data?.items ?? [];

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
    <div className="space-y-3">
      {items.map((quote) => (
        <Link key={quote.id} href={`/portal/quotations/${quote.id}`} className="block">
          <Card className="transition-colors hover:border-primary/40">
            <CardContent className="flex items-center justify-between p-5">
              <div>
                <p className="font-medium">Quotation {quote.reference}</p>
                <p className="text-sm text-muted-foreground">
                  {quote.lines.length} item{quote.lines.length === 1 ? "" : "s"} ·{" "}
                  <span
                    className={cn(
                      ACTIONABLE.has(quote.status) ? "font-medium text-foreground" : ""
                    )}
                  >
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
      ))}
    </div>
  );
}
