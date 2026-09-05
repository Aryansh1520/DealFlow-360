import { apiClient } from "@/lib/api-client";
import type { SubscriptionPlanCreate, SubscriptionPlanRead, SubscriptionPlanUpdate } from "@/lib/api/types";
import type { ListParams, Page } from "@/lib/types";

export const subscriptionPlansApi = {
  list: async (params: ListParams): Promise<Page<SubscriptionPlanRead>> => {
    const { data } = await apiClient.get<Page<SubscriptionPlanRead>>("/subscription-plans", {
      params,
    });
    return data;
  },

  create: async (payload: SubscriptionPlanCreate): Promise<SubscriptionPlanRead> => {
    const { data } = await apiClient.post<SubscriptionPlanRead>("/subscription-plans", payload);
    return data;
  },

  update: async (id: number, payload: SubscriptionPlanUpdate): Promise<SubscriptionPlanRead> => {
    const { data } = await apiClient.patch<SubscriptionPlanRead>(
      `/subscription-plans/${id}`,
      payload
    );
    return data;
  },

  remove: async (id: number): Promise<void> => {
    await apiClient.delete(`/subscription-plans/${id}`);
  },
};
