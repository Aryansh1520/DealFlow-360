"use client";

import { useRouter } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { Money } from "@/components/ui/money";
import { Skeleton } from "@/components/ui/skeleton";
import type { QuotationRead } from "@/lib/api/types";
import { useEnums } from "@/features/meta/hooks";
import { useQuotations } from "@/features/quotations/hooks";

function daysInactive(lastActivityAt: string): number {
  return Math.max(0, Math.floor((Date.now() - new Date(lastActivityAt).getTime()) / 86_400_000));
}

export function PipelineBoard() {
  const { data: enums } = useEnums();
  const { data, isLoading } = useQuotations({ page: 1, page_size: 100 });

  if (isLoading || !enums) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        {Array.from({ length: 5 }).map((_, index) => (
          <Skeleton key={index} className="h-96 w-full" />
        ))}
      </div>
    );
  }

  const terminalStatuses = new Set(
    enums.quote_status.filter((status) => (enums.transitions[status] ?? []).length === 0)
  );
  const activeStatuses = enums.quote_status.filter((status) => !terminalStatuses.has(status));
  const columns = [...activeStatuses, "closed"];

  const quotations = data?.items ?? [];
  const byColumn = (column: string) =>
    column === "closed"
      ? quotations.filter((q) => terminalStatuses.has(q.status))
      : quotations.filter((q) => q.status === column);

  return (
    <div className="flex gap-4 overflow-x-auto pb-4">
      {columns.map((column) => {
        const items = byColumn(column);
        return (
          <div key={column} className="w-72 shrink-0 space-y-2">
            <div className="flex items-center justify-between px-1">
              <p className="text-sm font-semibold">
                {column === "closed" ? "Closed" : enums.labels.quote_status?.[column] ?? column}
              </p>
              <Badge variant="secondary">{items.length}</Badge>
            </div>
            <div className="space-y-2">
              {items.length === 0 ? (
                <div className="rounded-lg border border-dashed p-4 text-center text-xs text-muted-foreground">
                  No quotations
                </div>
              ) : (
                items.map((quotation) => <PipelineCard key={quotation.id} quotation={quotation} />)
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function PipelineCard({ quotation }: { quotation: QuotationRead }) {
  const router = useRouter();
  const { trace } = quotation.computation;
  const riskTone =
    trace.risk_score < trace.thresholds.t1
      ? "positive"
      : trace.risk_score < trace.thresholds.t2
        ? "warning"
        : "danger";
  const inactive = daysInactive(quotation.last_activity_at);

  return (
    <button
      type="button"
      onClick={() => router.push(`/workspace/quotations/${quotation.id}`)}
      className="w-full space-y-2 rounded-lg border bg-card p-3 text-left shadow-sm transition-colors hover:bg-accent"
    >
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">{quotation.reference}</span>
        <Badge variant={riskTone}>{quotation.computation.risk_score}</Badge>
      </div>
      <p className="truncate text-sm text-muted-foreground">{quotation.customer_name}</p>
      <div className="flex items-center justify-between text-xs">
        <span className="font-medium tabular-nums">
          <Money minor={quotation.computation.total_minor} currency={quotation.currency} />
        </span>
        <span className={inactive > 5 ? "text-warning" : "text-muted-foreground"}>
          {inactive === 0 ? "Today" : `${inactive}d inactive`}
        </span>
      </div>
    </button>
  );
}
