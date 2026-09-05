"use client";

import * as React from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Download,
  FileText,
  Loader2,
  Receipt,
  Repeat,
  ShoppingCart,
} from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { getErrorMessage } from "@/lib/api-client";
import { useIdempotencyKey } from "@/lib/api/idempotency";
import { useInvalidateOnFrame, useLiveEvents } from "@/lib/live/use-live-events";
import type { BillingScheduleEntry, InvoiceRead, QuotationRead } from "@/lib/api/types";
import { PermissionGuard } from "@/features/auth/components/permission-guard";
import { useAuth } from "@/features/auth/auth-context";
import { QuotationTabs } from "@/features/quotations/components/quotation-tabs";
import { useQuotation } from "@/features/quotations/hooks";
import {
  useBillingSchedule,
  useDownloadInvoicePdf,
  useGenerateInvoice,
  useInvoices,
} from "@/features/billing/hooks";
import { InvoiceLineage } from "@/features/billing/components/invoice-lineage";
import { PaymentDialog } from "@/features/billing/components/payment-dialog";
import { SupersedeDialog } from "@/features/billing/components/supersede-dialog";

export function BillingScreen({ quotationId }: { quotationId: number }) {
  const { data: quote, isLoading: quoteLoading } = useQuotation(quotationId);
  const { data: schedule, isLoading: schedLoading } = useBillingSchedule(quotationId);
  const { data: invoicePage, isLoading: invLoading } = useInvoices(quotationId);

  const invalidate = useInvalidateOnFrame();
  useLiveEvents(`quote:${quotationId}`, invalidate);

  if (quoteLoading || schedLoading || invLoading) {
    return <Skeleton className="h-[32rem] w-full" />;
  }

  const invoices = invoicePage?.items ?? [];

  return (
    <PermissionGuard permissions={["billing:read"]}>
      <div>
        <Link
          href={`/workspace/quotations/${quotationId}`}
          className="mb-4 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" /> Back to quotation
        </Link>
        <QuotationTabs quotationId={quotationId} />

        <div className="mb-6 flex items-center gap-3">
          <h1 className="text-2xl font-semibold tracking-tight">Billing</h1>
          {quote && <StatusBadge status={quote.status} />}
        </div>

        <div className="space-y-8">
          <div className="grid gap-6 lg:grid-cols-2">
            <OneTimePanel quote={quote} />
            <RecurringPanel schedule={schedule ?? []} />
          </div>

          <InvoicesPanel
            quotationId={quotationId}
            quote={quote}
            invoices={invoices}
          />
        </div>
      </div>
    </PermissionGuard>
  );
}

/* -------------------------------------------------------------- one-time panel */

function OneTimePanel({ quote }: { quote: QuotationRead | undefined }) {
  const oneTime = (quote?.lines ?? []).filter((l) => l.line_type === "one_time");
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <ShoppingCart className="h-4 w-4 text-muted-foreground" />
          One-time charges
        </CardTitle>
        <CardDescription>Invoiced once, immediately.</CardDescription>
      </CardHeader>
      <CardContent>
        {oneTime.length === 0 ? (
          <p className="text-sm text-muted-foreground">No one-time lines on this order.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Product</TableHead>
                <TableHead className="text-right">Qty</TableHead>
                <TableHead className="text-right">Net</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {oneTime.map((line) => (
                <TableRow key={line.id}>
                  <TableCell className="font-medium">{line.product_name}</TableCell>
                  <TableCell className="text-right tabular-nums">{line.quantity}</TableCell>
                  <TableCell className="text-right">
                    <Money minor={line.net_minor} currency={quote!.currency} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}

/* ------------------------------------------------------------- recurring panel */

function RecurringPanel({ schedule }: { schedule: BillingScheduleEntry[] }) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Repeat className="h-4 w-4 text-muted-foreground" />
          Recurring — upcoming schedule
        </CardTitle>
        <CardDescription>One row per billing period. Prorated periods are marked.</CardDescription>
      </CardHeader>
      <CardContent>
        {schedule.length === 0 ? (
          <p className="text-sm text-muted-foreground">No subscription lines on this order.</p>
        ) : (
          <div className="max-h-80 overflow-y-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Period</TableHead>
                  <TableHead className="text-right">Amount</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {schedule.map((row) => (
                  <TableRow key={row.id}>
                    <TableCell className="whitespace-nowrap">
                      {new Date(row.period_start).toLocaleDateString()} –{" "}
                      {new Date(row.period_end).toLocaleDateString()}
                      {row.is_prorated && (
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Badge variant="warning" className="ml-2">
                                Prorated
                              </Badge>
                            </TooltipTrigger>
                            <TooltipContent>
                              Prorated: {row.proration_days} of {row.proration_basis_days} days
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <Money minor={row.amount_minor} currency={row.currency} />
                    </TableCell>
                    <TableCell>
                      <span className="text-xs capitalize text-muted-foreground">{row.status}</span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/* --------------------------------------------------------------- invoices panel */

function InvoicesPanel({
  quotationId,
  quote,
  invoices,
}: {
  quotationId: number;
  quote: QuotationRead | undefined;
  invoices: InvoiceRead[];
}) {
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("billing:write");
  const [genSeq, setGenSeq] = React.useState(0);
  const genKey = useIdempotencyKey(`gen-invoice-${quotationId}-${genSeq}`);
  const generate = useGenerateInvoice(quotationId);

  const canGenerate =
    canWrite && ["confirmed", "fulfilling", "invoiced"].includes(quote?.status ?? "");

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <div>
          <CardTitle className="flex items-center gap-2 text-base">
            <Receipt className="h-4 w-4 text-muted-foreground" />
            Invoices &amp; credit notes
          </CardTitle>
          <CardDescription>
            An issued document is immutable — corrections go through supersede.
          </CardDescription>
        </div>
        {canGenerate && (
          <Button
            size="sm"
            disabled={generate.isPending}
            onClick={() => {
              setGenSeq((n) => n + 1);
              generate.mutate(genKey);
            }}
          >
            {generate.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <FileText className="h-4 w-4" />
            )}
            Generate invoice
          </Button>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {invoices.length === 0 ? (
          <Alert>
            <AlertTitle>No invoices yet</AlertTitle>
            <AlertDescription>
              {canGenerate
                ? "Generate one when a period is due — one-time lines invoice immediately."
                : "Invoices appear here once billing issues them."}
            </AlertDescription>
          </Alert>
        ) : (
          invoices.map((invoice) => (
            <InvoiceRow
              key={invoice.id}
              quotationId={quotationId}
              invoice={invoice}
              canWrite={canWrite}
            />
          ))
        )}
      </CardContent>
    </Card>
  );
}

function InvoiceRow({
  quotationId,
  invoice,
  canWrite,
}: {
  quotationId: number;
  invoice: InvoiceRead;
  canWrite: boolean;
}) {
  const [payOpen, setPayOpen] = React.useState(false);
  const [supersedeOpen, setSupersedeOpen] = React.useState(false);
  const download = useDownloadInvoicePdf();

  const isCredit = invoice.document_type === "credit_note";
  const isSuperseded = invoice.status === "superseded";
  const actionable = canWrite && !isCredit && !isSuperseded;

  return (
    <div
      className={cn(
        "rounded-lg border p-4",
        isSuperseded && "border-dashed opacity-70",
        isCredit && "border-warning/40 bg-warning/5"
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-sm font-medium">{invoice.number}</span>
            <Badge variant={isCredit ? "warning" : "secondary"}>
              {isCredit ? "Credit note" : "Invoice"}
            </Badge>
            <span
              className={cn(
                "text-xs capitalize",
                invoice.status === "paid" && "text-positive",
                isSuperseded && "text-muted-foreground"
              )}
            >
              {invoice.status}
            </span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            {invoice.issued_at
              ? `Issued ${new Date(invoice.issued_at).toLocaleDateString()}`
              : "Draft"}
            {" · "}
            {invoice.lines.length} line{invoice.lines.length === 1 ? "" : "s"}
          </p>
        </div>
        <div className="text-right">
          <p className="font-semibold">
            <Money minor={invoice.total_minor} currency={invoice.currency} />
          </p>
          {!isCredit && invoice.balance_minor > 0 && (
            <p className="text-xs text-warning">
              <Money minor={invoice.balance_minor} currency={invoice.currency} /> outstanding
            </p>
          )}
        </div>
      </div>

      <div className="mt-3 space-y-1 border-t pt-3 text-sm">
        {invoice.lines.map((line, i) => (
          <div key={i} className="flex justify-between text-muted-foreground">
            <span>
              {line.description} <span className="text-xs">×{line.quantity}</span>
            </span>
            <Money minor={line.amount_minor} currency={invoice.currency} />
          </div>
        ))}
      </div>

      {(invoice.supersedes_invoice_id || invoice.superseded_by_invoice_id) && (
        <div className="mt-3">
          <InvoiceLineage invoiceId={invoice.id} />
        </div>
      )}

      <div className="mt-3 flex flex-wrap gap-2">
        <Button
          size="sm"
          variant="outline"
          disabled={download.isPending}
          onClick={() => download.mutate({ id: invoice.id, number: invoice.number })}
        >
          {download.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Download className="h-4 w-4" />
          )}
          PDF
        </Button>
        {actionable && invoice.status === "issued" && (
          <>
            <Button size="sm" onClick={() => setPayOpen(true)}>
              Record payment
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setSupersedeOpen(true)}>
              Supersede
            </Button>
          </>
        )}
        {isSuperseded && (
          <span className="self-center text-xs text-muted-foreground">
            Superseded — read-only
          </span>
        )}
      </div>

      {payOpen && (
        <PaymentDialog
          quotationId={quotationId}
          invoice={invoice}
          open={payOpen}
          onOpenChange={setPayOpen}
        />
      )}
      {supersedeOpen && (
        <SupersedeDialog
          quotationId={quotationId}
          invoice={invoice}
          open={supersedeOpen}
          onOpenChange={setSupersedeOpen}
        />
      )}
    </div>
  );
}
