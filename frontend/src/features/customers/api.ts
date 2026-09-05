import { apiClient } from "@/lib/api-client";
import type { ListParams, Page } from "@/lib/types";
import type { Customer, CustomerTier } from "@/features/auth/types";

export interface CustomerListParams extends ListParams {
  tier?: CustomerTier;
  portal_enabled?: boolean;
}

export interface CustomerCreatePayload {
  name: string;
  email: string;
  password: string;
  company?: string | null;
  phone?: string | null;
  tier?: CustomerTier;
  portal_enabled?: boolean;
}

export type CustomerUpdatePayload = Partial<CustomerCreatePayload>;

export const customersApi = {
  list: async (params: CustomerListParams): Promise<Page<Customer>> => {
    const { data } = await apiClient.get<Page<Customer>>("/customers", { params });
    return data;
  },

  create: async (payload: CustomerCreatePayload): Promise<Customer> => {
    const { data } = await apiClient.post<Customer>("/customers", payload);
    return data;
  },

  update: async (id: number, payload: CustomerUpdatePayload): Promise<Customer> => {
    const { data } = await apiClient.patch<Customer>(`/customers/${id}`, payload);
    return data;
  },

  remove: async (id: number): Promise<void> => {
    await apiClient.delete(`/customers/${id}`);
  },
};
