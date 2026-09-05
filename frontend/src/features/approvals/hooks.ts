"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { getErrorMessage } from "@/lib/api-client";
import { approvalsApi, type ApprovalQueueParams } from "@/features/approvals/api";
import { QUOTATIONS_KEY } from "@/features/quotations/hooks";

const APPROVALS_KEY = "approvals";

export function useApprovalQueue(params: ApprovalQueueParams) {
  return useQuery({
    queryKey: [APPROVALS_KEY, "queue", params],
    queryFn: () => approvalsApi.queue(params),
  });
}

export function useApproval(id: number) {
  return useQuery({
    queryKey: [APPROVALS_KEY, id],
    queryFn: () => approvalsApi.get(id),
  });
}

export function useApprovalChain(quotationId: number | null) {
  return useQuery({
    queryKey: [APPROVALS_KEY, "chain", quotationId],
    queryFn: () => approvalsApi.chainForQuotation(quotationId!),
    enabled: quotationId != null,
  });
}

export function useActOnApproval(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      action,
      reason,
      idempotencyKey,
    }: {
      action: "approve" | "reject" | "return_for_revision";
      reason?: string;
      idempotencyKey: string;
    }) => approvalsApi.act(id, { action, reason }, idempotencyKey),
    onSuccess: (quotation) => {
      queryClient.invalidateQueries({ queryKey: [APPROVALS_KEY] });
      queryClient.setQueryData([QUOTATIONS_KEY, quotation.id], quotation);
      queryClient.invalidateQueries({ queryKey: [QUOTATIONS_KEY, quotation.id, "events"] });
      if (quotation.status === "pending_l2") {
        toast.success("Approved — now pending Finance review");
      } else if (quotation.status === "approved") {
        toast.success("Approved — approval chain complete");
      } else if (quotation.status === "rejected") {
        toast.success("Rejected");
      } else if (quotation.status === "returned_for_revision") {
        toast.success("Returned for revision");
      }
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}
