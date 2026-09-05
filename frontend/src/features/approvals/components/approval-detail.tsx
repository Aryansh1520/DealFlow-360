"use client";

import * as React from "react";
import { Check, CheckCircle2, Circle, Loader2, RotateCcw, X, XCircle } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Money } from "@/components/ui/money";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/ui/status-badge";
import { getErrorMessage } from "@/lib/api-client";
import { useIdempotencyKey } from "@/lib/api/idempotency";
import type { ApprovalRead } from "@/lib/api/types";
import { useAuth } from "@/features/auth/auth-context";
import { useEnumLabel } from "@/features/meta/hooks";
import { useApproval, useApprovalChain, useActOnApproval } from "@/features/approvals/hooks";
import { ApprovalActionDialog } from "@/features/approvals/components/approval-action-dialog";
import { DecisionTracePanel } from "@/features/approvals/components/decision-trace";
import { LineTable } from "@/features/quotations/components/line-table";
import { useDecisionTrace, useQuotation } from "@/features/quotations/hooks";

const LEVEL_PERMISSION: Record<string, string> = {
  l1_sales_manager: "approvals:l1",
  l2_finance: "approvals:l2",
};

interface ActionRequest {
  action: "reject" | "return_for_revision";
  nonce: number;
}

export function ApprovalDetail({ approvalId }: { approvalId: number }) {
  const { hasPermission } = useAuth();
  const { data: approval, isLoading, isError, error } = useApproval(approvalId);
  const { data: quotation } = useQuotation(approval?.quotation_id ?? 0);
  const { data: trace } = useDecisionTrace(approval?.quotation_id ?? 0, Boolean(approval));
  const { data: chain } = useApprovalChain(approval?.quotation_id ?? null);

  const [actionRequest, setActionRequest] = React.useState<ActionRequest | null>(null);
  const [approveOpen, setApproveOpen] = React.useState(false);
  const act = useActOnApproval(approvalId);
  const approveIdemKey = useIdempotencyKey(`approve-${approvalId}`);

  if (isError) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Failed to load approval</AlertTitle>
        <AlertDescription>{getErrorMessage(error)}</AlertDescription>
      </Alert>
    );
  }

  if (isLoading || !approval || !quotation) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  const canAct = hasPermission(LEVEL_PERMISSION[approval.level] ?? "") && approval.status === "pending";

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-card p-4 shadow-sm">
        <div>
          <h1 className="text-lg font-semibold">{approval.quotation_reference}</h1>
          <p className="text-sm text-muted-foreground">
            {approval.customer_name} ·{" "}
            <Money minor={approval.total_minor} currency={approval.currency} />
          </p>
        </div>
        <StatusBadge status={quotation.status} />
      </div>

      {chain && chain.length > 0 && (
        <div className="rounded-lg border bg-card p-4 shadow-sm">
          <h2 className="mb-3 text-sm font-semibold">Approval chain</h2>
          <ChainStepper chain={chain} />
        </div>
      )}

      {canAct && (
        <div className="flex flex-wrap gap-2 rounded-lg border bg-card p-4 shadow-sm">
          <Button onClick={() => setApproveOpen(true)}>
            <Check />
            Approve
          </Button>
          <Button
            variant="outline"
            onClick={() => setActionRequest({ action: "return_for_revision", nonce: Date.now() })}
          >
            <RotateCcw />
            Return for revision
          </Button>
          <Button
            variant="destructive"
            onClick={() => setActionRequest({ action: "reject", nonce: Date.now() })}
          >
            <X />
            Reject
          </Button>
        </div>
      )}

      <div className="rounded-lg border bg-card p-4 shadow-sm">
        <h2 className="mb-3 text-sm font-semibold">Quotation (read-only)</h2>
        <LineTable
          lines={quotation.lines}
          currency={quotation.currency}
          previewTrace={null}
          editable={false}
          onQuantityChange={() => {}}
          onDiscountCommit={() => {}}
          onRemove={() => {}}
        />
      </div>

      {trace && (
        <div className="rounded-lg border bg-card p-4 shadow-sm">
          <h2 className="mb-3 text-sm font-semibold">Decision trace</h2>
          <DecisionTracePanel trace={trace} />
        </div>
      )}

      <ConfirmDialog
        open={approveOpen}
        onOpenChange={setApproveOpen}
        title="Approve this quotation?"
        description="This action is recorded against your name and cannot be undone from here."
        confirmLabel="Approve"
        isPending={act.isPending}
        onConfirm={() =>
          act.mutateAsync({ action: "approve", idempotencyKey: approveIdemKey }).catch(() => {})
        }
      />

      <ApprovalActionDialog
        key={actionRequest?.nonce}
        approvalId={approvalId}
        action={actionRequest?.action ?? null}
        onOpenChange={(open) => !open && setActionRequest(null)}
      />
    </div>
  );
}

function ChainStepper({ chain }: { chain: ApprovalRead[] }) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      {chain.map((step, index) => (
        <React.Fragment key={step.id}>
          <StepBadge step={step} />
          {index < chain.length - 1 && <Separator className="w-6" orientation="horizontal" />}
        </React.Fragment>
      ))}
    </div>
  );
}

function StepBadge({ step }: { step: ApprovalRead }) {
  const levelLabel = useEnumLabel("approval_level", step.level);
  const Icon =
    step.status === "approved"
      ? CheckCircle2
      : step.status === "rejected"
        ? XCircle
        : step.status === "returned"
          ? RotateCcw
          : step.status === "pending"
            ? Loader2
            : Circle;
  const tone =
    step.status === "approved"
      ? "text-positive"
      : step.status === "rejected"
        ? "text-danger"
        : step.status === "returned"
          ? "text-warning"
          : step.status === "pending"
            ? "text-info"
            : "text-muted-foreground";

  return (
    <div className="flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm">
      <Icon className={`h-4 w-4 ${tone} ${step.status === "pending" ? "animate-pulse" : ""}`} />
      <span className="font-medium">{levelLabel}</span>
      <Badge variant="outline" className="capitalize">
        {step.status}
      </Badge>
      {step.acted_by_name && <span className="text-xs text-muted-foreground">by {step.acted_by_name}</span>}
    </div>
  );
}
