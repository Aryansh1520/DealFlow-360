"use client";

import * as React from "react";
import Link from "next/link";
import { ArrowLeft, CheckCircle2, Loader2, MessageSquarePlus, Radio, Send } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { BpsInput } from "@/components/ui/bps-input";
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatBps } from "@/lib/money";
import { cn } from "@/lib/utils";
import { getErrorMessage } from "@/lib/api-client";
import { useIdempotencyKey } from "@/lib/api/idempotency";
import { useInvalidateOnFrame, useLiveEvents } from "@/lib/live/use-live-events";
import type { PortalQuotationRead } from "@/lib/api/types";
import {
  usePortalComment,
  usePortalConfirm,
  usePortalCounter,
  usePortalQuotation,
} from "@/features/portal/hooks";

/** Customer-facing status wording — never "pending_l1". */
const STATUS_COPY: Record<string, { label: string; tone: string }> = {
  sent: { label: "Awaiting your review", tone: "text-info" },
  under_negotiation: { label: "Under negotiation", tone: "text-warning" },
  confirmed: { label: "Confirmed", tone: "text-positive" },
  pending_l1: { label: "With our team for approval", tone: "text-muted-foreground" },
  pending_l2: { label: "With our team for approval", tone: "text-muted-foreground" },
  approved: { label: "Approved — ready to confirm", tone: "text-positive" },
  fulfilling: { label: "Being prepared for delivery", tone: "text-positive" },
  invoiced: { label: "Invoiced", tone: "text-positive" },
  paid: { label: "Paid — thank you", tone: "text-positive" },
  expired: { label: "Expired", tone: "text-muted-foreground" },
  cancelled: { label: "Cancelled", tone: "text-muted-foreground" },
};

export function NegotiationScreen({ quotationId }: { quotationId: number }) {
  const { data: quote, isLoading, isError, error } = usePortalQuotation(quotationId);

  const invalidate = useInvalidateOnFrame();
  const [flash, setFlash] = React.useState<string | null>(null);
  const { connected } = useLiveEvents(`quote:${quotationId}`, (frame) => {
    if (frame.event_type === "heartbeat") return;
    setFlash("Your rep just made a change — updating…");
    window.setTimeout(() => setFlash(null), 2500);
    invalidate(frame);
  });

  if (isLoading) return <Skeleton className="h-[32rem] w-full" />;
  if (isError || !quote) {
    return (
      <Alert variant="destructive">
        <AlertTitle>We couldn&apos;t load this quotation</AlertTitle>
        <AlertDescription>{getErrorMessage(error)}</AlertDescription>
      </Alert>
    );
  }

  const status = STATUS_COPY[quote.status] ?? { label: quote.status, tone: "text-muted-foreground" };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Link
          href="/portal/quotations"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" /> All quotations
        </Link>
        <span
          className="inline-flex items-center gap-1.5 text-xs text-muted-foreground"
          title={connected ? "Live — changes appear automatically" : "Reconnecting…"}
        >
          <Radio className={cn("h-3.5 w-3.5", connected ? "text-positive" : "text-muted-foreground/40")} />
          {connected ? "Live" : "Offline"}
        </span>
      </div>

      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Your quotation</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Reference {quote.reference} · <span className={cn("font-medium", status.tone)}>{status.label}</span>
          {quote.valid_until && ` · valid until ${new Date(quote.valid_until).toLocaleDateString()}`}
        </p>
      </div>

      {flash && (
        <Alert>
          <Loader2 className="h-4 w-4 animate-spin" />
          <AlertDescription>{flash}</AlertDescription>
        </Alert>
      )}

      <ReEnteredApprovalNotice quote={quote} />

      <LineTable quote={quote} />

      <div className="grid gap-6 md:grid-cols-2">
        <CounterCard quote={quote} />
        <ConfirmCard quote={quote} />
      </div>

      <TimelineCard quote={quote} />
    </div>
  );
}

/* ------------------------------------------------------------------ line table */

function LineTable({ quote }: { quote: PortalQuotationRead }) {
  const [commentFor, setCommentFor] = React.useState<number | null>(null);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">What&apos;s included</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Product</TableHead>
                <TableHead className="text-right">Qty</TableHead>
                <TableHead className="text-right">Unit price</TableHead>
                <TableHead className="text-right">Discount</TableHead>
                <TableHead className="text-right">Line total</TableHead>
                <TableHead className="w-10" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {quote.lines.map((line) => (
                <React.Fragment key={line.id}>
                  <TableRow>
                    <TableCell className="font-medium">{line.product_name}</TableCell>
                    <TableCell className="text-right tabular-nums">{line.quantity}</TableCell>
                    <TableCell className="text-right">
                      <Money minor={line.unit_price_minor} currency={quote.currency} />
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {line.discount_bps > 0 ? formatBps(line.discount_bps) : "—"}
                    </TableCell>
                    <TableCell className="text-right">
                      <Money minor={line.net_minor} currency={quote.currency} />
                    </TableCell>
                    <TableCell>
                      {quote.can_counter && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7"
                          title="Comment on this line"
                          onClick={() =>
                            setCommentFor((current) => (current === line.id ? null : line.id))
                          }
                        >
                          <MessageSquarePlus className="h-4 w-4" />
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                  {commentFor === line.id && (
                    <TableRow>
                      <TableCell colSpan={6} className="bg-muted/40">
                        <LineComposer
                          quoteId={quote.id}
                          lineId={line.id}
                          onDone={() => setCommentFor(null)}
                        />
                      </TableCell>
                    </TableRow>
                  )}
                </React.Fragment>
              ))}
            </TableBody>
          </Table>
        </div>

        <dl className="ml-auto max-w-xs space-y-1.5 text-sm">
          <Row label="Subtotal">
            <Money minor={quote.totals.gross_minor} currency={quote.currency} />
          </Row>
          <Row label="Discount">
            <Money minor={quote.totals.discount_total_minor} currency={quote.currency} />
          </Row>
          <Row label="Tax">
            <Money minor={quote.totals.tax_minor} currency={quote.currency} />
          </Row>
          <Row label="Total" strong>
            <Money minor={quote.totals.total_minor} currency={quote.currency} />
          </Row>
        </dl>
      </CardContent>
    </Card>
  );
}

function Row({
  label,
  children,
  strong,
}: {
  label: string;
  children: React.ReactNode;
  strong?: boolean;
}) {
  return (
    <div className={cn("flex justify-between", strong && "border-t pt-1.5 font-semibold")}>
      <dt className="text-muted-foreground">{label}</dt>
      <dd>{children}</dd>
    </div>
  );
}

function LineComposer({
  quoteId,
  lineId,
  onDone,
}: {
  quoteId: number;
  lineId: number;
  onDone: () => void;
}) {
  const [body, setBody] = React.useState("");
  const comment = usePortalComment(quoteId);
  return (
    <form
      className="flex items-center gap-2 py-1"
      onSubmit={(e) => {
        e.preventDefault();
        if (!body.trim()) return;
        comment.mutate({ line_id: lineId, body }, { onSuccess: onDone });
      }}
    >
      <Input
        autoFocus
        placeholder="Ask a question about this line…"
        value={body}
        onChange={(e) => setBody(e.target.value)}
      />
      <Button type="submit" size="sm" disabled={comment.isPending || !body.trim()}>
        {comment.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Send"}
      </Button>
      <Button type="button" size="sm" variant="ghost" onClick={onDone}>
        Cancel
      </Button>
    </form>
  );
}

/* --------------------------------------------------------------- counter card */

function CounterCard({ quote }: { quote: PortalQuotationRead }) {
  const [bps, setBps] = React.useState(0);
  const [message, setMessage] = React.useState("");
  const counter = usePortalCounter(quote.id);

  if (!quote.can_counter) return <div className="hidden md:block" />;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Request a better price</CardTitle>
        <CardDescription>
          Ask for an overall discount. Your rep reviews it — it isn&apos;t applied automatically.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form
          className="space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            counter.mutate(
              { requested_discount_bps: bps, message: message || null },
              {
                onSuccess: () => {
                  setBps(0);
                  setMessage("");
                },
              }
            );
          }}
        >
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Requested discount</label>
            <BpsInput value={bps} onChange={setBps} />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">Message (optional)</label>
            <Input
              placeholder="A note for your rep…"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
            />
          </div>
          <Button type="submit" variant="secondary" disabled={counter.isPending || bps <= 0}>
            {counter.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            Submit request
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

/* --------------------------------------------------------------- confirm card */

function ConfirmCard({ quote }: { quote: PortalQuotationRead }) {
  const [dialogSeq, setDialogSeq] = React.useState(0);
  const idempotencyKey = useIdempotencyKey(`portal-confirm-${quote.id}-${dialogSeq}`);
  const confirm = usePortalConfirm(quote.id);
  const [result, setResult] = React.useState<{ status: string; reEntered: boolean } | null>(null);

  if (result?.reEntered) {
    return (
      <Alert>
        <AlertTitle>Thanks — your requested terms need internal approval</AlertTitle>
        <AlertDescription>
          We&apos;ll be back to you shortly. Nothing more to do for now.
        </AlertDescription>
      </Alert>
    );
  }
  if (result && !result.reEntered) {
    return (
      <Alert>
        <CheckCircle2 className="h-4 w-4 text-positive" />
        <AlertTitle>Quotation confirmed</AlertTitle>
        <AlertDescription>Your order is confirmed. Thank you!</AlertDescription>
      </Alert>
    );
  }

  // Already confirmed / being fulfilled / invoiced / paid — nothing to do here.
  const DONE: Record<string, string> = {
    confirmed: "This quotation is confirmed — your order is being prepared.",
    fulfilling: "Your order is confirmed and being prepared for delivery.",
    invoiced: "Your order is confirmed and has been invoiced.",
    paid: "This order is confirmed and paid in full. Thank you!",
  };
  if (DONE[quote.status]) {
    return (
      <Alert>
        <CheckCircle2 className="h-4 w-4 text-positive" />
        <AlertTitle>All set</AlertTitle>
        <AlertDescription>{DONE[quote.status]}</AlertDescription>
      </Alert>
    );
  }

  const notYet =
    quote.status === "expired"
      ? "This quotation has expired — ask your rep for a fresh one."
      : quote.status === "cancelled"
        ? "This quotation was cancelled."
        : "Your rep is still preparing this quotation — you'll be able to confirm once it's sent to you.";

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Ready to go ahead?</CardTitle>
        <CardDescription>
          Confirming accepts the quotation on its current terms.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Button
          className="w-full"
          disabled={!quote.can_confirm || confirm.isPending}
          onClick={() => {
            setDialogSeq((n) => n + 1);
            confirm.mutate(
              { expectedVersion: quote.version, idempotencyKey },
              {
                onSuccess: (res) =>
                  setResult({ status: res.status, reEntered: res.re_entered_approval }),
              }
            );
          }}
        >
          {confirm.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <CheckCircle2 className="h-4 w-4" />
          )}
          Confirm quotation
        </Button>
        {!quote.can_confirm && (
          <p className="mt-2 text-xs text-muted-foreground">{notYet}</p>
        )}
      </CardContent>
    </Card>
  );
}

function ReEnteredApprovalNotice({ quote }: { quote: PortalQuotationRead }) {
  if (quote.status !== "pending_l1" && quote.status !== "pending_l2") return null;
  // Covers both a fresh quote still in internal sign-off and a quote that
  // re-entered approval after the customer requested different terms.
  const askedForChanges = quote.timeline.some((e) => e.event_type === "quote.customer_countered");
  return (
    <Alert>
      <AlertTitle>
        {askedForChanges ? "Your requested terms are with our team" : "Being finalised by our team"}
      </AlertTitle>
      <AlertDescription>
        {askedForChanges
          ? "We're reviewing the changes you asked for and will update this page as soon as there's news."
          : "This quotation is going through internal sign-off. You'll be able to confirm it once it's approved."}
      </AlertDescription>
    </Alert>
  );
}

/* -------------------------------------------------------------- timeline card */

function TimelineCard({ quote }: { quote: PortalQuotationRead }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Activity</CardTitle>
      </CardHeader>
      <CardContent>
        {quote.timeline.length === 0 ? (
          <p className="text-sm text-muted-foreground">Nothing has happened yet.</p>
        ) : (
          <ol className="space-y-3">
            {quote.timeline
              .slice()
              .reverse()
              .map((entry, i) => (
                <li key={i} className="flex gap-3 text-sm">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-muted-foreground/50" />
                  <div>
                    <p>{entry.summary}</p>
                    <p className="text-xs text-muted-foreground">
                      {entry.actor_label} · {new Date(entry.created_at).toLocaleString()}
                    </p>
                  </div>
                </li>
              ))}
          </ol>
        )}
      </CardContent>
    </Card>
  );
}
