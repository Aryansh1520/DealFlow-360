"use client";

import * as React from "react";
import { HelpCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Bps, Money } from "@/components/ui/money";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import type { QuoteComputation } from "@/lib/api/types";

interface TotalsBlockProps {
  computation: QuoteComputation | null;
  isFetching: boolean;
  onOpenTrace: () => void;
  className?: string;
  /** Rendered above the totals — the builder passes the quotation header
   * (reference, customer, headline amount) so the two merge into one card. */
  header?: React.ReactNode;
  /** Rendered pinned to the bottom — the builder passes the submit / cancel
   * actions. */
  footer?: React.ReactNode;
}

/** Gross → discount → net → tax → total, margin bar, risk chip, approval
 * preview. `FRONTEND_PHASE_2.md` Task 2d: "the rep knows before submitting,
 * not after" — every number is `computation`, nothing computed here. */
export function TotalsBlock({
  computation,
  isFetching,
  onOpenTrace,
  className,
  header,
  footer,
}: TotalsBlockProps) {
  // Task 3: "the margin bar must visibly move" — flash briefly whenever the
  // total actually changes (e.g. an upsell lands), not on every re-render.
  const [flash, setFlash] = React.useState(false);
  const lastTotal = React.useRef<number | null>(null);
  React.useEffect(() => {
    if (!computation) return;
    const changed = lastTotal.current !== null && lastTotal.current !== computation.total_minor;
    lastTotal.current = computation.total_minor;
    if (changed) {
      setFlash(true);
      const timer = setTimeout(() => setFlash(false), 400);
      return () => clearTimeout(timer);
    }
  }, [computation]);

  return (
    <div
      className={cn(
        "flex flex-col gap-4 overflow-y-auto rounded-lg border bg-card p-4 shadow-sm transition-all duration-300",
        isFetching && "opacity-70",
        flash && "ring-2 ring-info",
        className
      )}
    >
      {header}
      {isFetching && computation && (
        <div className="h-0.5 w-full shrink-0 animate-pulse rounded-full bg-primary/40" />
      )}
      {computation ? (
        <TotalsBody computation={computation} onOpenTrace={onOpenTrace} />
      ) : (
        <div className="flex flex-1 items-center justify-center rounded-lg border border-dashed p-4 text-center text-sm text-muted-foreground">
          Add a line to see live totals.
        </div>
      )}
      {footer}
    </div>
  );
}

function TotalsBody({
  computation,
  onOpenTrace,
}: {
  computation: QuoteComputation;
  onOpenTrace: () => void;
}) {
  const { trace } = computation;
  const riskTone =
    trace.risk_score < trace.thresholds.t1
      ? "positive"
      : trace.risk_score < trace.thresholds.t2
        ? "warning"
        : "danger";
  const marginTone = computation.margin_bps < 0 ? "danger" : computation.margin_bps < 1800 ? "warning" : "positive";
  const marginToneClass = {
    positive: "bg-positive",
    warning: "bg-warning",
    danger: "bg-danger",
  }[marginTone];

  return (
    <div className="space-y-4">
      <dl className="space-y-1.5 text-sm">
        <Row label="Gross" value={<Money minor={computation.gross_minor} currency={computation.currency} />} />
        <Row
          label="Discount"
          value={
            <span className="text-muted-foreground">
              −<Money minor={computation.discount_total_minor} currency={computation.currency} />
            </span>
          }
        />
        <Row label="Net" value={<Money minor={computation.net_minor} currency={computation.currency} />} />
        <Row label="Tax" value={<Money minor={computation.tax_minor} currency={computation.currency} />} />
        <Separator />
        <Row
          label={<span className="font-semibold">Total</span>}
          value={
            <span className="text-lg font-semibold">
              <Money minor={computation.total_minor} currency={computation.currency} />
            </span>
          }
        />
      </dl>

      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>Margin</span>
          <Bps value={computation.margin_bps} />
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
          <div
            className={cn("h-full rounded-full transition-all", marginToneClass)}
            style={{ width: `${Math.min(100, Math.max(0, computation.margin_bps / 100))}%` }}
          />
        </div>
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Risk</span>
          <Badge variant={riskTone}>{trace.risk_score}/100</Badge>
        </div>
        <button
          type="button"
          onClick={onOpenTrace}
          className="flex items-center gap-1 text-xs font-medium text-primary hover:underline"
        >
          Why? <HelpCircle className="h-3 w-3" />
        </button>
      </div>
    </div>
  );
}

/** The approval outcome as a single coloured capsule — meant to sit inline with
 * the quotation's customer / tier / rep line, not as a block in the totals body. */
export function ApprovalBadge({ computation }: { computation: QuoteComputation | null }) {
  if (!computation) return null;

  if (computation.trace.outcome === "blocked") {
    return <Badge variant="danger">Below cost</Badge>;
  }
  if (computation.required_approvals.length === 0) {
    return <Badge variant="positive">Auto-approve</Badge>;
  }
  const needsL2 = computation.required_approvals.includes("l2_finance");
  return <Badge variant="warning">{needsL2 ? "Needs L1 + L2" : "Needs L1"}</Badge>;
}

function Row({ label, value }: { label: React.ReactNode; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="tabular-nums">{value}</dd>
    </div>
  );
}
