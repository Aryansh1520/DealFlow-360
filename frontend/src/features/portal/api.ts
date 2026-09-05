import { apiClient, type TokenPair } from "@/lib/api-client";
import type {
  PortalConfirmResponse,
  PortalQuotationRead,
} from "@/lib/api/types";
import type { ListParams, Page } from "@/lib/types";

export interface PortalCounterPayload {
  requested_discount_bps: number;
  line_id?: number | null;
  message?: string | null;
}

export interface PortalCommentPayload {
  line_id?: number | null;
  body: string;
}

export const portalApi = {
  /** Unauthenticated — this is how a customer principal is born. */
  redeem: async (token: string): Promise<TokenPair & { quotation_id: number }> => {
    const { data } = await apiClient.post<TokenPair & { quotation_id: number }>(
      "/portal/magic-link/redeem",
      { token }
    );
    return data;
  },

  list: async (params: ListParams): Promise<Page<PortalQuotationRead>> => {
    const { data } = await apiClient.get<Page<PortalQuotationRead>>("/portal/quotations", {
      params,
    });
    return data;
  },

  get: async (id: number): Promise<PortalQuotationRead> => {
    const { data } = await apiClient.get<PortalQuotationRead>(`/portal/quotations/${id}`);
    return data;
  },

  comment: async (id: number, payload: PortalCommentPayload): Promise<PortalQuotationRead> => {
    const { data } = await apiClient.post<PortalQuotationRead>(
      `/portal/quotations/${id}/comments`,
      payload
    );
    return data;
  },

  counter: async (id: number, payload: PortalCounterPayload): Promise<PortalQuotationRead> => {
    const { data } = await apiClient.post<PortalQuotationRead>(
      `/portal/quotations/${id}/counter`,
      payload
    );
    return data;
  },

  confirm: async (
    id: number,
    expectedVersion: number,
    idempotencyKey: string
  ): Promise<PortalConfirmResponse> => {
    const { data } = await apiClient.post<PortalConfirmResponse>(
      `/portal/quotations/${id}/confirm`,
      { expected_version: expectedVersion },
      { headers: { "Idempotency-Key": idempotencyKey } }
    );
    return data;
  },
};
