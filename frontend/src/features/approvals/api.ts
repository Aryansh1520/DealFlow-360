import { apiClient } from "@/lib/api-client";
import { USE_MOCKS } from "@/lib/config";
import { toApiError } from "@/lib/api/mock/error-bridge";
import * as mock from "@/lib/api/mock/store";
import type { ApprovalRead, QuotationRead } from "@/lib/api/types";
import type { Actor } from "@/features/quotations/api";

export interface ApprovalQueueParams {
  level?: string;
  status?: string;
}

export const approvalsApi = {
  queue: async (params: ApprovalQueueParams): Promise<ApprovalRead[]> => {
    if (USE_MOCKS) return mock.listApprovals(params);
    const { data } = await apiClient.get<ApprovalRead[]>("/approvals/queue", { params });
    return data;
  },

  get: async (id: number): Promise<ApprovalRead> => {
    if (USE_MOCKS) return mock.getApproval(id).catch(toApiError);
    const { data } = await apiClient.get<ApprovalRead>(`/approvals/${id}`);
    return data;
  },

  /** Every approval sequence for one quotation, for the chain stepper — see
   * the contract-gap note on `mock/store.ts::listApprovalsForQuotation`. The
   * real-backend fallback filters the documented queue endpoint client-side
   * since there's no dedicated endpoint for this yet. */
  chainForQuotation: async (quotationId: number): Promise<ApprovalRead[]> => {
    if (USE_MOCKS) return mock.listApprovalsForQuotation(quotationId);
    const { data } = await apiClient.get<ApprovalRead[]>("/approvals/queue");
    return data.filter((a) => a.quotation_id === quotationId);
  },

  act: async (
    id: number,
    payload: { action: "approve" | "reject" | "return_for_revision"; reason?: string },
    idempotencyKey: string,
    actor: Actor
  ): Promise<QuotationRead> => {
    if (USE_MOCKS) {
      return mock.actOnApproval(id, payload.action, payload.reason, actor).catch(toApiError);
    }
    const { data } = await apiClient.post<QuotationRead>(`/approvals/${id}/act`, payload, {
      headers: { "Idempotency-Key": idempotencyKey },
    });
    return data;
  },
};
