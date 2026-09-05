"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Radio, RefreshCw, Send } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Money } from "@/components/ui/money";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/ui/status-badge";
import { cn } from "@/lib/utils";
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
import { TotalsBlock } from "@/features/quotations/components/totals-block";
import { UpsellPanel } from "@/features/quotations/components/upsell-panel";
import { editorReducer, quotationToEditorState } from "@/features/quotations/editor-reducer";
import {
  useAddLine,
  useQuotation,
  useRemoveLine,
  useSubmitQuotation,
  useTransitionQuotation,
  useUpdateLine,
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

  // Manual escape hatch — one click re-pulls the quote, its timeline, the
  // suggestions and the decision trace (all keyed under ["quotations", id]).
  const handleRefresh = React.useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["quotations", quotationId] });
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

  const [traceOpen, setTraceOpen] = React.useState(false);
  const [confirmSubmitOpen, setConfirmSubmitOpen] = React.useState(false);
  const [confirmCancelOpen, setConfirmCancelOpen] = React.useState(false);

  const submitIntentId = quotation ? `submit-${quotation.id}-${quotation.version}` : "submit";
  const submitIdemKey = useIdempotencyKey(submitIntentId);
  const cancelIntentId = quotation ? `cancel-${quotation.id}-${quotation.version}` : "cancel";
  const cancelIdemKey = useIdempotencyKey(cancelIntentId);

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

  // The quotation header (reference, customer, headline amount) and the submit /
  // cancel actions are handed to <TotalsBlock> as its `header` / `footer` so the
  // amount and the live totals read as one card.
  const summaryHeader = (
    <div className="shrink-0">
      <div className="flex items-center gap-2">
        <h1 className="text-lg font-semibold">{quotation.reference}</h1>
        <StatusBadge status={quotation.status} />
      </div>
      <p className="mt-1 text-sm text-muted-foreground">
        {quotation.customer_name} · <span className="capitalize">{quotation.customer_tier}</span> ·{" "}
        {quotation.owner_rep_name}
      </p>
      <p className="mt-2 text-xl font-semibold tabular-nums">
        <Money minor={quotation.computation.total_minor} currency={quotation.currency} />
      </p>
      <Separator className="mt-3" />
    </div>
  );

  const summaryFooter =
    canSubmit || canCancel ? (
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

      <CounterRequestBanner quotation={quotation} />

      {!editable && quotation.status.startsWith("pending_") && (
        <Alert>
          <AlertTitle>Awaiting approval</AlertTitle>
          <AlertDescription>
            This quotation is in the approval queue. Editing a line here is allowed, but it
            will invalidate any approval already granted and re-route the quote from scratch.
          </AlertDescription>
        </Alert>
      )}
      {quotation.status === "approved" && (
        <Alert>
          <AlertTitle>Already approved</AlertTitle>
          <AlertDescription>
            Editing a line will skip the existing approval and re-run the decision engine —
            the quote may need to go through approval again before it can be sent.
          </AlertDescription>
        </Alert>
      )}

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
    </div>
  );
}
