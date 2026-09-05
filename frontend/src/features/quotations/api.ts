import { apiClient } from "@/lib/api-client";
import { USE_MOCKS } from "@/lib/config";
import { toApiError } from "@/lib/api/mock/error-bridge";
import * as mock from "@/lib/api/mock/store";
import type {
  DecisionTrace,
  PreviewLine,
  QuotationRead,
  QuoteComputation,
  QuoteEventRead,
  SuggestionRead,
} from "@/lib/api/types";
import type { ListParams, Page } from "@/lib/types";

/** The `{id, name}` pair the mock store records against events/approvals —
 * a stand-in for what the real backend derives server-side from the JWT. */
export interface Actor {
  id: number;
  name: string;
}

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
    if (USE_MOCKS) {
      return mock.listQuotations({
        status: params.status,
        owner_rep_id: params.owner_rep_id,
        customer_id: params.customer_id,
        q: params.q ?? params.search,
        page: params.page ?? 1,
        page_size: params.page_size ?? 20,
      });
    }
    const { data } = await apiClient.get<Page<QuotationRead>>("/quotations", { params });
    return data;
  },

  get: async (id: number): Promise<QuotationRead> => {
    if (USE_MOCKS) return mock.getQuotation(id).catch(toApiError);
    const { data } = await apiClient.get<QuotationRead>(`/quotations/${id}`);
    return data;
  },

  create: async (payload: QuotationCreatePayload, actor: Actor): Promise<QuotationRead> => {
    if (USE_MOCKS) {
      return mock.createQuotation(payload.customer_id, payload.valid_until ?? null, actor).catch(toApiError);
    }
    const { data } = await apiClient.post<QuotationRead>("/quotations", payload);
    return data;
  },

  update: async (
    id: number,
    payload: { expected_version: number; order_discount_bps?: number; valid_until?: string | null },
    actor: Actor
  ): Promise<QuotationRead> => {
    if (USE_MOCKS) {
      return mock
        .updateQuotation(id, payload.expected_version, payload, actor)
        .catch(toApiError);
    }
    const { data } = await apiClient.patch<QuotationRead>(`/quotations/${id}`, payload);
    return data;
  },

  addLine: async (id: number, payload: AddLinePayload, actor: Actor): Promise<QuotationRead> => {
    if (USE_MOCKS) {
      return mock
        .addLine(
          id,
          payload.expected_version,
          {
            product_id: payload.product_id,
            variant_id: payload.variant_id ?? null,
            quantity: payload.quantity,
            discount_bps: payload.discount_bps,
            from_suggestion: payload.from_suggestion,
          },
          actor
        )
        .catch(toApiError);
    }
    const { data } = await apiClient.post<QuotationRead>(`/quotations/${id}/lines`, payload);
    return data;
  },

  updateLine: async (
    id: number,
    lineId: number,
    payload: UpdateLinePayload,
    actor: Actor
  ): Promise<QuotationRead> => {
    if (USE_MOCKS) {
      return mock.updateLine(id, lineId, payload.expected_version, payload, actor).catch(toApiError);
    }
    const { data } = await apiClient.patch<QuotationRead>(
      `/quotations/${id}/lines/${lineId}`,
      payload
    );
    return data;
  },

  removeLine: async (
    id: number,
    lineId: number,
    expectedVersion: number,
    actor: Actor
  ): Promise<QuotationRead> => {
    if (USE_MOCKS) {
      return mock.removeLine(id, lineId, expectedVersion, actor).catch(toApiError);
    }
    const { data } = await apiClient.delete<QuotationRead>(`/quotations/${id}/lines/${lineId}`, {
      params: { expected_version: expectedVersion },
    });
    return data;
  },

  preview: async (id: number, payload: PreviewPayload, signal?: AbortSignal): Promise<QuoteComputation> => {
    if (USE_MOCKS) return mock.preview(id, payload).catch(toApiError);
    const { data } = await apiClient.post<QuoteComputation>(`/quotations/${id}/preview`, payload, {
      signal,
    });
    return data;
  },

  submit: async (
    id: number,
    payload: { expected_version: number },
    idempotencyKey: string,
    actor: Actor
  ): Promise<QuotationRead> => {
    if (USE_MOCKS) {
      return mock.submitQuotation(id, payload.expected_version, actor).catch(toApiError);
    }
    const { data } = await apiClient.post<QuotationRead>(`/quotations/${id}/submit`, payload, {
      headers: { "Idempotency-Key": idempotencyKey },
    });
    return data;
  },

  transition: async (
    id: number,
    payload: { expected_version: number; to_status: string; reason?: string },
    idempotencyKey: string,
    actor: Actor
  ): Promise<QuotationRead> => {
    if (USE_MOCKS) {
      return mock
        .transitionQuotation(id, payload.expected_version, payload.to_status, payload.reason, actor)
        .catch(toApiError);
    }
    const { data } = await apiClient.post<QuotationRead>(`/quotations/${id}/transition`, payload, {
      headers: { "Idempotency-Key": idempotencyKey },
    });
    return data;
  },

  events: async (id: number, params: ListParams): Promise<Page<QuoteEventRead>> => {
    if (USE_MOCKS) return mock.listEvents(id, params.page ?? 1, params.page_size ?? 20);
    const { data } = await apiClient.get<Page<QuoteEventRead>>(`/quotations/${id}/events`, {
      params,
    });
    return data;
  },

  decisionTrace: async (id: number): Promise<DecisionTrace> => {
    if (USE_MOCKS) return mock.getDecisionTrace(id).catch(toApiError);
    const { data } = await apiClient.get<DecisionTrace>(`/quotations/${id}/decision-trace`);
    return data;
  },

  suggestions: async (id: number, limit = 5): Promise<SuggestionRead[]> => {
    if (USE_MOCKS) return mock.getSuggestions(id, limit);
    const { data } = await apiClient.get<SuggestionRead[]>(`/quotations/${id}/suggestions`, {
      params: { limit },
    });
    return data;
  },

  dismissSuggestion: async (id: number, productId: number, actor: Actor): Promise<void> => {
    if (USE_MOCKS) return mock.dismissSuggestion(id, productId, actor);
    await apiClient.post(`/quotations/${id}/suggestions/${productId}/dismiss`);
  },
};
