"use client";

import * as React from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowLeft,
  Boxes,
  CheckCircle2,
  Layers,
  Loader2,
  PackageCheck,
  Truck,
} from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Money } from "@/components/ui/money";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/ui/status-badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { getErrorMessage, InsufficientStockError } from "@/lib/api-client";
import { useIdempotencyKey } from "@/lib/api/idempotency";
import { useInvalidateOnFrame, useLiveEvents } from "@/lib/live/use-live-events";
import type { AllocationInput, FulfillmentPlan, QuotationRead } from "@/lib/api/types";
import { PermissionGuard } from "@/features/auth/components/permission-guard";
import { QuotationTabs } from "@/features/quotations/components/quotation-tabs";
import { useQuotation } from "@/features/quotations/hooks";
import { useAllWarehouses } from "@/features/warehouses/hooks";
import {
  useAcceptPlan,
  useConsolidateBackorders,
  useFulfillmentPlan,
  useOverridePlan,
} from "@/features/fulfillment/hooks";

export function FulfillmentScreen({ quotationId }: { quotationId: number }) {
  const { data: quote, isLoading: quoteLoading } = useQuotation(quotationId);
  const { data: plan, isLoading: planLoading, isError, error } = useFulfillmentPlan(quotationId);

  const invalidate = useInvalidateOnFrame();
  useLiveEvents(`quote:${quotationId}`, invalidate);

  if (quoteLoading || planLoading) return <Skeleton className="h-[32rem] w-full" />;

  return (
    <PermissionGuard permissions={["fulfillment:read"]}>
      <div>
        <Link
          href={`/workspace/quotations/${quotationId}`}
          className="mb-4 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" /> Back to quotation
        </Link>
        <QuotationTabs quotationId={quotationId} />

        <div className="mb-6 flex items-center gap-3">
          <h1 className="text-2xl font-semibold tracking-tight">Fulfilment</h1>
          {quote && <StatusBadge status={quote.status} />}
          {quote?.fulfillment_status && (
            <span className="rounded-full border px-2 py-0.5 text-xs text-muted-foreground">
              {quote.fulfillment_status}
            </span>
          )}
        </div>

        {isError || !plan ? (
          <Alert variant="destructive">
            <AlertTitle>Couldn&apos;t compute a fulfilment plan</AlertTitle>
            <AlertDescription>{getErrorMessage(error)}</AlertDescription>
          </Alert>
        ) : (
          <PlanView quotationId={quotationId} plan={plan} quote={quote} />
        )}
      </div>
    </PermissionGuard>
  );
}

function PlanView({
  quotationId,
  plan,
  quote,
}: {
  quotationId: number;
  plan: FulfillmentPlan;
  quote: QuotationRead | undefined;
}) {
  const [overrideOpen, setOverrideOpen] = React.useState(false);
  const canAct =
    quote?.status === "confirmed" || quote?.status === "fulfilling";

  return (
    <div className="space-y-6">
      {/* Optimisation strip — the two numbers the allocator optimises for. */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <StatTile
          icon={<Layers className="h-4 w-4" />}
          label="Shipments"
          value={String(plan.shipment_count)}
        />
        <StatTile
          icon={<Truck className="h-4 w-4" />}
          label="Est. shipping cost"
          value={<Money minor={plan.estimated_shipping_cost_minor} currency={plan.currency} />}
        />
        <StatTile
          icon={
            plan.fully_allocatable ? (
              <CheckCircle2 className="h-4 w-4 text-positive" />
            ) : (
              <AlertTriangle className="h-4 w-4 text-warning" />
            )
          }
          label="Coverage"
          value={plan.fully_allocatable ? "Fully allocatable" : "Partial — see backorders"}
        />
      </div>

      {/* Suggested split */}
      <div className="grid gap-4 md:grid-cols-2">
        {plan.shipments.map((shipment, i) => (
          <Card key={`${shipment.warehouse_id}-${i}`}>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center justify-between text-base">
                <span className="flex items-center gap-2">
                  <Boxes className="h-4 w-4 text-muted-foreground" />
                  {shipment.warehouse_name}
                </span>
                <span className="text-xs font-normal text-muted-foreground">
                  cost weight {shipment.shipping_cost_weight}
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-1.5 text-sm">
                {shipment.lines.map((line) => (
                  <li key={line.line_id} className="flex justify-between">
                    <span>{line.product_name}</span>
                    <span className="tabular-nums text-muted-foreground">×{line.quantity}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        ))}
        {plan.shipments.length === 0 && (
          <p className="text-sm text-muted-foreground">
            Nothing can ship right now — every line is on backorder.
          </p>
        )}
      </div>

      {/* Backorders */}
      {!plan.fully_allocatable && (
        <Alert variant="warning">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Some lines can&apos;t be fully allocated</AlertTitle>
          <AlertDescription>
            <ul className="mt-2 space-y-1 text-sm">
              {plan.backorders.map((b) => (
                <li key={b.line_id} className="flex justify-between">
                  <span>
                    {b.product_name} — {b.quantity} short
                  </span>
                  <span className="text-muted-foreground">
                    {b.expected_restock_at
                      ? `restock ~${new Date(b.expected_restock_at).toLocaleDateString()}`
                      : "no restock date"}
                  </span>
                </li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      )}

      {/* Actions */}
      {canAct ? (
        <div className="flex flex-wrap items-center gap-3">
          <AcceptButton quotationId={quotationId} plan={plan} quote={quote} />
          <Button variant="outline" onClick={() => setOverrideOpen((v) => !v)}>
            {overrideOpen ? "Hide manual override" : "Manual override"}
          </Button>
          {quote?.status === "fulfilling" && (
            <ConsolidateButton quotationId={quotationId} quote={quote} plan={plan} />
          )}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">
          The quotation must be <strong>confirmed</strong> before a fulfilment plan can be accepted.
        </p>
      )}

      {overrideOpen && quote && (
        <OverrideTable quotationId={quotationId} plan={plan} quote={quote} />
      )}
    </div>
  );
}

function StatTile({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode;
}) {
  return (
    <Card>
      <CardContent className="p-4">
        <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
          {icon} {label}
        </p>
        <p className="mt-1 text-lg font-semibold">{value}</p>
      </CardContent>
    </Card>
  );
}

function AcceptButton({
  quotationId,
  plan,
  quote,
}: {
  quotationId: number;
  plan: FulfillmentPlan;
  quote: QuotationRead | undefined;
}) {
  const key = useIdempotencyKey(`accept-plan-${quotationId}-${quote?.version}-${plan.plan_hash}`);
  const accept = useAcceptPlan(quotationId);
  return (
    <Button
      disabled={!quote || accept.isPending}
      onClick={() =>
        accept.mutate({
          expectedVersion: quote!.version,
          planHash: plan.plan_hash,
          idempotencyKey: key,
        })
      }
    >
      {accept.isPending ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : (
        <PackageCheck className="h-4 w-4" />
      )}
      Accept suggested split
    </Button>
  );
}

function ConsolidateButton({
  quotationId,
  quote,
  plan,
}: {
  quotationId: number;
  quote: QuotationRead;
  plan: FulfillmentPlan;
}) {
  const key = useIdempotencyKey(`consolidate-${quotationId}-${quote.version}`);
  const consolidate = useConsolidateBackorders(quotationId);
  if (plan.fully_allocatable && plan.backorders.length === 0) return null;
  return (
    <Button
      variant="secondary"
      disabled={consolidate.isPending}
      onClick={() =>
        consolidate.mutate({ expectedVersion: quote.version, idempotencyKey: key })
      }
    >
      {consolidate.isPending ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : (
        <Boxes className="h-4 w-4" />
      )}
      Consolidate remaining backorder
    </Button>
  );
}

/* ------------------------------------------------------------- manual override */

function OverrideTable({
  quotationId,
  plan,
  quote,
}: {
  quotationId: number;
  plan: FulfillmentPlan;
  quote: QuotationRead;
}) {
  const { data: warehousePage } = useAllWarehouses();
  const warehouses = warehousePage?.items ?? [];
  const override = useOverridePlan(quotationId);
  const key = useIdempotencyKey(`override-${quotationId}-${quote.version}`);

  // Shippable (one_time) lines only.
  const lines = quote.lines.filter((l) => l.line_type === "one_time");

  // rows keyed "lineId:warehouseId" -> qty
  const [rows, setRows] = React.useState<Record<string, number>>(() => {
    const seed: Record<string, number> = {};
    for (const s of plan.shipments) {
      for (const ln of s.lines) seed[`${ln.line_id}:${s.warehouse_id}`] = ln.quantity;
    }
    return seed;
  });

  const shortfalls =
    override.error instanceof InsufficientStockError
      ? ((override.error.data.shortfalls as ShortfallRow[] | undefined) ?? [])
      : [];

  const perLineTotal = (lineId: number) =>
    warehouses.reduce((sum, w) => sum + (rows[`${lineId}:${w.id}`] || 0), 0);

  const allocations: AllocationInput[] = Object.entries(rows)
    .map(([k, qty]) => {
      const [lineId, warehouseId] = k.split(":").map(Number);
      return { line_id: lineId, warehouse_id: warehouseId, quantity: qty };
    })
    .filter((a) => a.quantity > 0);

  const anyMismatch = lines.some((l) => perLineTotal(l.id) > l.quantity);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Manual allocation</CardTitle>
        <CardDescription>
          Set quantities per warehouse. The client check is a hint — the backend is the
          authority and will return the exact shortfall if stock has moved.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Line</TableHead>
                <TableHead className="text-right">Ordered</TableHead>
                {warehouses.map((w) => (
                  <TableHead key={w.id} className="text-right">
                    {w.code}
                  </TableHead>
                ))}
                <TableHead className="text-right">Allocated</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {lines.map((line) => {
                const allocated = perLineTotal(line.id);
                const over = allocated > line.quantity;
                return (
                  <TableRow key={line.id}>
                    <TableCell className="font-medium">{line.product_name}</TableCell>
                    <TableCell className="text-right tabular-nums">{line.quantity}</TableCell>
                    {warehouses.map((w) => (
                      <TableCell key={w.id} className="text-right">
                        <Input
                          type="number"
                          min={0}
                          className="ml-auto h-8 w-20 text-right tabular-nums"
                          value={rows[`${line.id}:${w.id}`] ?? 0}
                          onChange={(e) =>
                            setRows((r) => ({
                              ...r,
                              [`${line.id}:${w.id}`]: Math.max(0, Number(e.target.value) || 0),
                            }))
                          }
                        />
                      </TableCell>
                    ))}
                    <TableCell
                      className={cn(
                        "text-right font-medium tabular-nums",
                        over ? "text-danger" : allocated === line.quantity ? "text-positive" : ""
                      )}
                    >
                      {allocated}
                      {allocated < line.quantity && " (backorder)"}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>

        {shortfalls.length > 0 && (
          <Alert variant="destructive">
            <AlertTitle>Backend rejected the allocation</AlertTitle>
            <AlertDescription>
              <ul className="mt-1 space-y-1 text-sm">
                {shortfalls.map((s, i) => (
                  <li key={i}>
                    Line {s.line_id} at warehouse {s.warehouse_id}: asked {s.requested}, only{" "}
                    {s.available} available.
                  </li>
                ))}
              </ul>
            </AlertDescription>
          </Alert>
        )}

        <Button
          disabled={override.isPending || anyMismatch || allocations.length === 0}
          onClick={() =>
            override.mutate({
              expectedVersion: quote.version,
              allocations,
              idempotencyKey: key,
            })
          }
        >
          {override.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          Save manual allocation
        </Button>
        {anyMismatch && (
          <p className="text-xs text-danger">
            One or more lines are allocated above their ordered quantity.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

interface ShortfallRow {
  line_id: number;
  warehouse_id: number;
  requested: number;
  available: number;
}
