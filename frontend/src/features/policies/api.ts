import { apiClient } from "@/lib/api-client";
import type { PolicyCreate, PolicyRead } from "@/lib/api/types";
import type { ListParams, Page } from "@/lib/types";

export const policiesApi = {
  list: async (params: ListParams): Promise<Page<PolicyRead>> => {
    const { data } = await apiClient.get<Page<PolicyRead>>("/policies", { params });
    return data;
  },

  active: async (): Promise<PolicyRead> => {
    const { data } = await apiClient.get<PolicyRead>("/policies/active");
    return data;
  },

  create: async (payload: PolicyCreate): Promise<PolicyRead> => {
    const { data } = await apiClient.post<PolicyRead>("/policies", payload);
    return data;
  },

  activate: async (id: number): Promise<PolicyRead> => {
    const { data } = await apiClient.post<PolicyRead>(`/policies/${id}/activate`);
    return data;
  },
};
