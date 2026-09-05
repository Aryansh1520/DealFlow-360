import { apiClient } from "@/lib/api-client";
import type { AllocationInput, FulfillmentPlan, QuotationRead } from "@/lib/api/types";

export const fulfillmentApi = {
  plan: async (quotationId: number): Promise<FulfillmentPlan> => {
    const { data } = await apiClient.get<FulfillmentPlan>(
      `/quotations/${quotationId}/fulfillment/plan`
    );
    return data;
  },

  accept: async (
    quotationId: number,
    payload: { expected_version: number; plan_hash: string },
    idempotencyKey: string
  ): Promise<QuotationRead> => {
    const { data } = await apiClient.post<QuotationRead>(
      `/quotations/${quotationId}/fulfillment/accept`,
      payload,
      { headers: { "Idempotency-Key": idempotencyKey } }
    );
    return data;
  },

  override: async (
    quotationId: number,
    payload: { expected_version: number; allocations: AllocationInput[] },
    idempotencyKey: string
  ): Promise<QuotationRead> => {
    const { data } = await apiClient.post<QuotationRead>(
      `/quotations/${quotationId}/fulfillment/override`,
      payload,
      { headers: { "Idempotency-Key": idempotencyKey } }
    );
    return data;
  },

  consolidate: async (
    quotationId: number,
    payload: { expected_version: number },
    idempotencyKey: string
  ): Promise<QuotationRead> => {
    const { data } = await apiClient.post<QuotationRead>(
      `/quotations/${quotationId}/fulfillment/consolidate`,
      payload,
      { headers: { "Idempotency-Key": idempotencyKey } }
    );
    return data;
  },
};
