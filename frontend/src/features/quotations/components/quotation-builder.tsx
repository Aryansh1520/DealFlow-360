"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Radio, RefreshCw, Send } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { BpsInput } from "@/components/ui/bps-input";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/ui/status-badge";
import { cn } from "@/lib/utils";
import { formatBps } from "@/lib/money";
import { getErrorMessage } from "@/lib/api-client";
import { useIdempotencyKey } from "@/lib/api/idempotency";
import { useInvalidateOnFrame, useLiveEvents } from "@/lib/live/use-live-events";
import type { ProductRead, SuggestionRead } from "@/lib/api/types";
import { useAllowedTransitions } from "@/features/meta/hooks";
import { DecisionTraceDrawer } from "@/features/approvals/components/decision-trace-drawer";
import { CounterRequestBanner } from "@/features/quotations/components/counter-request-banner";
import { QuotationTabs } from "@/features/quotations/components/quotation-tabs";
import { CataloguePanel } from "@/features/quotations/components/catalogue-panel";
import { LineTable } from "@/features/quotations/components/line-table";
import { Timeline } from "@/features/quotations/components/timeline";
import { ApprovalBadge, TotalsBlock } from "@/features/quotations/components/totals-block";
import { UpsellPanel } from "@/features/quotations/components/upsell-panel";
import { editorReducer, quotationToEditorState } from "@/features/quotations/editor-reducer";
import {
  useAddLine,
  usePendingCounter,
  useQuotation,
  useRemoveLine,
  useSubmitQuotation,
  useTransitionQuotation,
  useUnsentChanges,
  useUpdateLine,
  useUpdateQuotation,
} from "@/features/quotations/hooks";
import { useQuotePreview } from "@/features/quotations/use-preview";

export function QuotationBuilder({ quotationId }: { quotationId: number }) {
  const {
    data: quotation,
    isLoading,
    isError,
    error,
    isRefetching,
  } = useQuotation(quotationId);
  const allowedTransitions = useAllowedTransitions(quotation?.status);
  const queryClient = useQueryClient();
  const router = useRouter();

  // Live: the customer's portal actions (comment, counter, confirm) land here
  // without a refresh — the two-window demo money shot.
  const invalidateOnFrame = useInvalidateOnFrame();
  const { connected: live } = useLiveEvents(`quote:${quotationId}`, invalidateOnFrame);

  const pendingCounter = usePendingCounter(quotationId);
  const unsentChanges = useUnsentChanges(quotationId, quotation?.status);

  // Manual escape hatch — one click re-pulls the quote, its timeline, the
  // suggestions and the decision trace (all keyed under ["quotations", id]).
  // `refetchType: "all"` so it's never weaker than the live SSE path (which uses
  // the same) — a collapsed panel or an unfocused tab still re-pulls.
  const handleRefresh = React.useCallback(() => {
    queryClient.invalidateQueries({
      queryKey: ["quotations", quotationId],
      refetchType: "all",
    });
  }, [queryClient, quotationId]);

  const [editorState, dispatch] = React.useReducer(
    editorReducer,
    quotation ? quotationToEditorState(quotation) : { lines: [], orderDiscountBps: 0 }
  );

  // Re-sync the editor whenever the persisted version changes (after any
  // commit, or on first load) — never on the debounced preview, which lives
  // in a separate query key and never touches this cache.
  const lastSyncedVersion = React.useRef<number | null>(null);
  React.useEffect(() => {
    if (quotation && lastSyncedVersion.current !== quotation.version) {
      dispatch({ type: "reset", quotation });
      lastSyncedVersion.current = quotation.version;
    }
  }, [quotation]);

  const { computation, isFetching: previewFetching } = useQuotePreview(quotationId, editorState);

  const addLine = useAddLine(quotationId);
  const updateLine = useUpdateLine(quotationId);
  const removeLine = useRemoveLine(quotationId);
  const submit = useSubmitQuotation(quotationId);
  const transition = useTransitionQuotation(quotationId);
  const updateQuotation = useUpdateQuotation(quotationId);

  const [traceOpen, setTraceOpen] = React.useState(false);
  const [confirmSubmitOpen, setConfirmSubmitOpen] = React.useState(false);
  const [confirmCancelOpen, setConfirmCancelOpen] = React.useState(false);
  const [confirmSendOpen, setConfirmSendOpen] = React.useState(false);

  // The customer's counter-offer stages its requested discount here rather than
  // auto-applying — the rep confirms and commits it themselves.
  const orderDiscountRef = React.useRef<HTMLInputElement>(null);
  const stageOrderDiscount = React.useCallback((requestedBps: number) => {
    dispatch({ type: "set_order_discount", discountBps: requestedBps });
    requestAnimationFrame(() => {
      orderDiscountRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
      orderDiscountRef.current?.focus();
    });
  }, []);

  const submitIntentId = quotation ? `submit-${quotation.id}-${quotation.version}` : "submit";
  const submitIdemKey = useIdempotencyKey(submitIntentId);
  const cancelIntentId = quotation ? `cancel-${quotation.id}-${quotation.version}` : "cancel";
  const cancelIdemKey = useIdempotencyKey(cancelIntentId);
  const sendIntentId = quotation ? `send-${quotation.id}-${quotation.version}` : "send";
  const sendIdemKey = useIdempotencyKey(sendIntentId);

  if (isLoading || !quotation) {
    return (
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
        <Skeleton className="h-[38rem] w-full" />
        <Skeleton className="h-[38rem] w-full" />
      </div>
    );
  }

  if (isError) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Failed to load quotation</AlertTitle>
        <AlertDescription>{getErrorMessage(error)}</AlertDescription>
      </Alert>
    );
  }

  // Matches the backend's actual `_LOCKED_STATUSES` (quotations/service.py) —
  // everything except these stays editable, including `pending_l1`,
  // `pending_l2` and `approved`. That's deliberate: editing a line there is
  // exactly what `DECISION_ENGINE.md` §8's "golden rule" exists to handle —
  // the backend re-runs the engine, skips stale approvals and re-routes
  // automatically the moment `approved_line_hash` no longer matches. The UI
  // must not be stricter than the backend or that flow can never be reached.
  const LOCKED_STATUSES = ["confirmed", "fulfilling", "invoiced", "paid", "rejected", "cancelled", "expired"];
  const editable = !LOCKED_STATUSES.includes(quotation.status);
  const isPendingApproval = quotation.status === "pending_l1" || quotation.status === "pending_l2";
  const canCancel = allowedTransitions.includes("cancelled");
  const canSubmit = quotation.status === "draft" || quotation.status === "returned_for_revision";
  const canSend = allowedTransitions.includes("sent");

  // While a counter-offer is open the rep may not stage MORE than the customer
  // asked for. With no open counter the field is unrestricted (the 0–100% clamp
  // still applies). Line-scoped counters carry an order-level ask too, so they
  // cap the same way.
  const orderDiscountCap =
    pendingCounter && pendingCounter.requestedBps > 0 ? pendingCounter.requestedBps : null;
  const orderDiscountOverCap =
    orderDiscountCap != null && editorState.orderDiscountBps > orderDiscountCap;

  const orderDiscountDirty = editorState.orderDiscountBps !== quotation.order_discount_bps;
  const orderDiscountBlocked = computation?.trace.outcome === "blocked";
  const commitOrderDiscount = () => {
    if (editorState.orderDiscountBps === quotation.order_discount_bps) return;
    if (orderDiscountOverCap) return;
    updateQuotation.mutate({
      expected_version: quotation.version,
      order_discount_bps: editorState.orderDiscountBps,
    });
  };

  const handleAddProduct = (product: ProductRead) => {
    addLine.mutate({
      expected_version: quotation.version,
      product_id: product.id,
      variant_id: null,
      quantity: 1,
      discount_bps: 0,
    });
  };

  const handleAddSuggestion = (suggestion: SuggestionRead) => {
    addLine.mutate({
      expected_version: quotation.version,
      product_id: suggestion.product_id,
      variant_id: null,
      quantity: suggestion.suggested_quantity,
      discount_bps: 0,
      from_suggestion: true,
    });
  };

  const handleQuantityChange = (lineId: number, quantity: number) => {
    if (quantity < 1) return;
    updateLine.mutate({ lineId, payload: { expected_version: quotation.version, quantity } });
  };

  const handleDiscountCommit = (lineId: number, discountBps: number) => {
    updateLine.mutate({
      lineId,
      payload: { expected_version: quotation.version, discount_bps: discountBps },
    });
  };

  const handleRemove = (lineId: number) => {
    removeLine.mutate({ lineId, expectedVersion: quotation.version });
  };

  // Errors already toast via each mutation's `onError` — swallow here so the
  // dialog doesn't produce an unhandled rejection on top of that. On success the
  // rep is dropped back on the quotations list: the quote is now the approver's
  // to move, and any later change surfaces through the header notification bell.
  const handleSubmit = () =>
    submit
      .mutateAsync({ expectedVersion: quotation.version, idempotencyKey: submitIdemKey })
      .then(() => router.push("/workspace/quotations"))
      .catch(() => {});

  const handleCancel = () =>
    transition
      .mutateAsync({
        toStatus: "cancelled",
        expectedVersion: quotation.version,
        idempotencyKey: cancelIdemKey,
      })
      .catch(() => {});

  const handleSend = () =>
    transition
      .mutateAsync({
        toStatus: "sent",
        expectedVersion: quotation.version,
        idempotencyKey: sendIdemKey,
      })
      .catch(() => {});

  // The quotation header (reference, customer) and the submit / cancel actions are
  // handed to <TotalsBlock> as its `header` / `footer` so they read as one card.
  // The headline amount is intentionally omitted — the live "Total" row in the
  // body is the single source of truth, and dropping it keeps the card scroll-free.
  const summaryHeader = (
    <div className="shrink-0">
      <div className="flex items-center gap-2">
        <h1 className="text-lg font-semibold">{quotation.reference}</h1>
        <StatusBadge status={quotation.status} />
      </div>
      <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted-foreground">
        <span>
          {quotation.customer_name} · <span className="capitalize">{quotation.customer_tier}</span> ·{" "}
          {quotation.owner_rep_name}
        </span>
        <ApprovalBadge computation={computation} />
      </div>
      <Separator className="mt-3" />
    </div>
  );

  const summaryFooter =
    canSubmit || canSend || canCancel ? (
      <div className="mt-auto flex shrink-0 flex-col gap-2 pt-2">
        {canSubmit && (
          <Button
            disabled={editorState.lines.length === 0}
            onClick={() => setConfirmSubmitOpen(true)}
          >
            <Send className="h-4 w-4" />
            Submit for Approval
          </Button>
        )}
        {canSend && (
          <Button onClick={() => setConfirmSendOpen(true)}>
            <Send className="h-4 w-4" />
            Send to Customer
          </Button>
        )}
        {canCancel && (
          <Button variant="outline" onClick={() => setConfirmCancelOpen(true)}>
            Cancel
          </Button>
        )}
      </div>
    ) : null;

  const summaryCard = (
    <TotalsBlock
      className="shrink-0 lg:h-[30.5rem]"
      header={summaryHeader}
      footer={summaryFooter}
      computation={computation}
      isFetching={previewFetching}
      onOpenTrace={() => setTraceOpen(true)}
    />
  );

  const lineTable = (className: string) => (
    <LineTable
      className={className}
      lines={quotation.lines}
      currency={quotation.currency}
      previewTrace={computation?.trace ?? null}
      editable={editable}
      onQuantityChange={handleQuantityChange}
      onDiscountCommit={handleDiscountCommit}
      onRemove={handleRemove}
    />
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-end gap-3">
        <span
          className="inline-flex items-center gap-1.5 text-xs text-muted-foreground"
          title={live ? "Live — customer actions appear automatically" : "Reconnecting…"}
        >
          <Radio className={cn("h-3.5 w-3.5", live ? "text-positive" : "text-muted-foreground/40")} />
          {live ? "Live" : "Offline"}
        </span>
        <Button
          variant="outline"
          size="sm"
          onClick={handleRefresh}
          disabled={isRefetching}
          title="Reload the latest version of this quotation"
        >
          <RefreshCw className={cn("h-3.5 w-3.5", isRefetching && "animate-spin")} />
          Refresh
        </Button>
      </div>

      <QuotationTabs quotationId={quotationId} />

      <CounterRequestBanner quotation={quotation} onStageOrderDiscount={stageOrderDiscount} />

      {!editable && quotation.status.startsWith("pending_") && (
        <Alert>
          <AlertTitle>Awaiting approval</AlertTitle>
          <AlertDescription>
            This quotation is in the approval queue. Editing a line here is allowed, but it
            will invalidate any approval already granted and re-route the quote from scratch.
          </AlertDescription>
        </Alert>
      )}
      {unsentChanges && canSend ? (
        <Alert>
          <AlertTitle>Not sent to the customer yet</AlertTitle>
          <AlertDescription>
            Your changes are saved, but the customer still sees the version you last sent
            them. They reach the customer only when you click <strong>Send to Customer</strong> —
            the flow picks up from there.
          </AlertDescription>
        </Alert>
      ) : quotation.status === "approved" ? (
        <Alert>
          <AlertTitle>Already approved</AlertTitle>
          <AlertDescription>
            Editing a line will skip the existing approval and re-run the decision engine —
            the quote may need to go through approval again before it can be sent.
          </AlertDescription>
        </Alert>
      ) : null}

      {/* Two columns. Left stack: catalogue, line items, activity. Right stack:
       * the merged amount + totals card, then suggestions. Both columns run the
       * same total height (62rem) so the right split lands at a clean half each
       * (30.5rem + 1rem gap + 30.5rem), and every card scrolls its own content
       * instead of growing the page. */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_320px] lg:items-start">
        <div className="flex min-w-0 flex-col gap-4">
          {editable && (
            <div className="flex shrink-0 flex-col overflow-hidden rounded-lg border bg-card p-3 shadow-sm lg:h-72">
              <CataloguePanel onAdd={handleAddProduct} />
            </div>
          )}
          {lineTable(editable ? "shrink-0 lg:h-[22rem]" : "shrink-0 lg:h-[41rem]")}
          {editable && (
            <div className="flex shrink-0 flex-col gap-2 rounded-lg border bg-card p-4 shadow-sm">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h2 className="text-sm font-semibold">Order discount</h2>
                  <p className="text-xs text-muted-foreground">
                    Applied across every line, on top of any per-line discount. Re-checks
                    approval; the customer isn&apos;t notified until you Send.
                  </p>
                </div>
                <div className="w-28 shrink-0">
                  <BpsInput
                    ref={orderDiscountRef}
                    value={editorState.orderDiscountBps}
                    maxBps={orderDiscountCap ?? undefined}
                    onChange={(bps) => dispatch({ type: "set_order_discount", discountBps: bps })}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        commitOrderDiscount();
                      }
                    }}
                    aria-label="Order-level discount percentage"
                  />
                </div>
              </div>
              {orderDiscountCap != null && (
                <p
                  className={cn(
                    "text-xs",
                    orderDiscountOverCap ? "font-medium text-danger" : "text-muted-foreground"
                  )}
                >
                  Capped at the {formatBps(orderDiscountCap)} {pendingCounter?.event.actor_name} asked
                  for — decline the counter to go higher.
                </p>
              )}
              {orderDiscountBlocked && (
                <p className="text-xs font-medium text-danger">
                  This discount prices a line below cost — it can’t be applied. Lower it first.
                </p>
              )}
              {orderDiscountDirty && (
                <div className="flex items-center justify-end gap-2">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() =>
                      dispatch({
                        type: "set_order_discount",
                        discountBps: quotation.order_discount_bps,
                      })
                    }
                  >
                    Reset
                  </Button>
                  <Button
                    size="sm"
                    disabled={updateQuotation.isPending || orderDiscountBlocked || orderDiscountOverCap}
                    onClick={commitOrderDiscount}
                  >
                    Apply order discount
                  </Button>
                </div>
              )}
            </div>
          )}
          <div className="flex min-h-0 shrink-0 flex-col rounded-lg border bg-card p-4 shadow-sm lg:h-80">
            <h2 className="mb-2 text-sm font-semibold">Activity</h2>
            <Separator className="mb-3" />
            <div className="min-h-0 flex-1 overflow-y-auto pr-1">
              <Timeline quotationId={quotationId} />
            </div>
          </div>
        </div>

        <div className="flex min-w-0 flex-col gap-4">
          {summaryCard}
          {editable ? (
            <div className="flex shrink-0 flex-col overflow-hidden rounded-lg border bg-card p-3 shadow-sm lg:h-[30.5rem]">
              <UpsellPanel quotationId={quotationId} onAdd={handleAddSuggestion} />
            </div>
          ) : (
            <div className="flex shrink-0 items-center justify-center rounded-lg border bg-card p-4 text-center text-sm text-muted-foreground shadow-sm lg:h-[30.5rem]">
              Suggestions are only available while editing.
            </div>
          )}
        </div>
      </div>

      <DecisionTraceDrawer quotationId={quotationId} open={traceOpen} onOpenChange={setTraceOpen} />

      <ConfirmDialog
        open={confirmSubmitOpen}
        onOpenChange={setConfirmSubmitOpen}
        title="Submit for approval?"
        description={
          computation && computation.required_approvals.length > 0
            ? "This will route the quotation into the approval queue based on the current risk score."
            : "This quotation is within policy and will be auto-approved."
        }
        confirmLabel="Submit"
        onConfirm={handleSubmit}
        isPending={submit.isPending}
      />
      <ConfirmDialog
        open={confirmCancelOpen}
        onOpenChange={setConfirmCancelOpen}
        title="Cancel this quotation?"
        description="This cannot be undone."
        confirmLabel="Cancel quotation"
        variant="destructive"
        onConfirm={handleCancel}
        isPending={transition.isPending}
      />
      <ConfirmDialog
        open={confirmSendOpen}
        onOpenChange={setConfirmSendOpen}
        title="Send this quotation to the customer?"
        description="They'll get a portal link and can confirm the current terms or send a counter-offer."
        confirmLabel="Send"
        onConfirm={handleSend}
        isPending={transition.isPending}
      />
    </div>
  );
}
