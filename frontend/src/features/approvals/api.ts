import { apiClient } from "@/lib/api-client";
import type { ApprovalRead, QuotationRead } from "@/lib/api/types";
import type { ListParams, Page } from "@/lib/types";

export interface ApprovalQueueParams extends ListParams {
  level?: string;
  status?: string;
}

export const approvalsApi = {
  queue: async (params: ApprovalQueueParams): Promise<Page<ApprovalRead>> => {
    const { data } = await apiClient.get<Page<ApprovalRead>>("/approvals/queue", { params });
    return data;
  },

  get: async (id: number): Promise<ApprovalRead> => {
    const { data } = await apiClient.get<ApprovalRead>(`/approvals/${id}`);
    return data;
  },

  /** Every approval sequence for one quotation, for the chain stepper.
   * `API_CONTRACT.md` §4.6 has no `quotation_id` filter on `/approvals/queue`,
   * so this fetches the (unfiltered-by-status) queue and filters client-side.
   * Fine at hackathon scale; ask Dev A for a dedicated filter if this needs
   * to scale further. */
  chainForQuotation: async (quotationId: number): Promise<ApprovalRead[]> => {
    const { data } = await apiClient.get<Page<ApprovalRead>>("/approvals/queue", {
      params: { page_size: 100 },
    });
    return data.items.filter((a) => a.quotation_id === quotationId);
  },

  act: async (
    id: number,
    payload: { action: "approve" | "reject" | "return_for_revision"; reason?: string },
    idempotencyKey: string
  ): Promise<QuotationRead> => {
    const { data } = await apiClient.post<QuotationRead>(`/approvals/${id}/act`, payload, {
      headers: { "Idempotency-Key": idempotencyKey },
    });
    return data;
  },
};
