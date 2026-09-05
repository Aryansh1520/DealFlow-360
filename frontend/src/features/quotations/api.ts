import { apiClient } from "@/lib/api-client";
import type {
  DecisionTrace,
  PreviewLine,
  QuotationRead,
  QuoteComputation,
  QuoteEventRead,
  SuggestionRead,
} from "@/lib/api/types";
import type { ListParams, Page } from "@/lib/types";

export interface QuotationListParams extends ListParams {
  status?: string;
  owner_rep_id?: number;
  customer_id?: number;
  stage?: string;
  q?: string;
  date_from?: string;
  date_to?: string;
}

export interface QuotationCreatePayload {
  customer_id: number;
  valid_until?: string | null;
}

export interface AddLinePayload {
  expected_version: number;
  product_id: number;
  variant_id?: number | null;
  quantity: number;
  discount_bps: number;
  from_suggestion?: boolean;
}

export interface UpdateLinePayload {
  expected_version: number;
  quantity?: number;
  discount_bps?: number;
}

export interface PreviewPayload {
  lines: PreviewLine[];
  order_discount_bps: number;
}

export const quotationsApi = {
  list: async (params: QuotationListParams): Promise<Page<QuotationRead>> => {
    const { data } = await apiClient.get<Page<QuotationRead>>("/quotations", { params });
    return data;
  },

  get: async (id: number): Promise<QuotationRead> => {
    const { data } = await apiClient.get<QuotationRead>(`/quotations/${id}`);
    return data;
  },

  create: async (payload: QuotationCreatePayload): Promise<QuotationRead> => {
    const { data } = await apiClient.post<QuotationRead>("/quotations", payload);
    return data;
  },

  update: async (
    id: number,
    payload: { expected_version: number; order_discount_bps?: number; valid_until?: string | null }
  ): Promise<QuotationRead> => {
    const { data } = await apiClient.patch<QuotationRead>(`/quotations/${id}`, payload);
    return data;
  },

  addLine: async (id: number, payload: AddLinePayload): Promise<QuotationRead> => {
    const { data } = await apiClient.post<QuotationRead>(`/quotations/${id}/lines`, payload);
    return data;
  },

  updateLine: async (id: number, lineId: number, payload: UpdateLinePayload): Promise<QuotationRead> => {
    const { data } = await apiClient.patch<QuotationRead>(
      `/quotations/${id}/lines/${lineId}`,
      payload
    );
    return data;
  },

  removeLine: async (id: number, lineId: number, expectedVersion: number): Promise<QuotationRead> => {
    const { data } = await apiClient.delete<QuotationRead>(`/quotations/${id}/lines/${lineId}`, {
      params: { expected_version: expectedVersion },
    });
    return data;
  },

  preview: async (id: number, payload: PreviewPayload, signal?: AbortSignal): Promise<QuoteComputation> => {
    const { data } = await apiClient.post<QuoteComputation>(`/quotations/${id}/preview`, payload, {
      signal,
    });
    return data;
  },

  submit: async (
    id: number,
    payload: { expected_version: number },
    idempotencyKey: string
  ): Promise<QuotationRead> => {
    const { data } = await apiClient.post<QuotationRead>(`/quotations/${id}/submit`, payload, {
      headers: { "Idempotency-Key": idempotencyKey },
    });
    return data;
  },

  transition: async (
    id: number,
    payload: { expected_version: number; to_status: string; reason?: string },
    idempotencyKey: string
  ): Promise<QuotationRead> => {
    const { data } = await apiClient.post<QuotationRead>(`/quotations/${id}/transition`, payload, {
      headers: { "Idempotency-Key": idempotencyKey },
    });
    return data;
  },

  rejectCounter: async (
    id: number,
    payload: { expected_version: number; reason?: string }
  ): Promise<QuotationRead> => {
    const { data } = await apiClient.post<QuotationRead>(`/quotations/${id}/counter/reject`, payload);
    return data;
  },

  events: async (id: number, params: ListParams): Promise<Page<QuoteEventRead>> => {
    const { data } = await apiClient.get<Page<QuoteEventRead>>(`/quotations/${id}/events`, {
      params,
    });
    return data;
  },

  decisionTrace: async (id: number): Promise<DecisionTrace> => {
    const { data } = await apiClient.get<DecisionTrace>(`/quotations/${id}/decision-trace`);
    return data;
  },

  suggestions: async (id: number, limit = 5): Promise<SuggestionRead[]> => {
    const { data } = await apiClient.get<SuggestionRead[]>(`/quotations/${id}/suggestions`, {
      params: { limit },
    });
    return data;
  },

  dismissSuggestion: async (id: number, productId: number): Promise<void> => {
    await apiClient.post(`/quotations/${id}/suggestions/${productId}/dismiss`);
  },
};
