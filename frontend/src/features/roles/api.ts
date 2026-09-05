import { apiClient } from "@/lib/api-client";
import type { ListParams, Page } from "@/lib/types";
import type { Role } from "@/features/auth/types";

export interface RoleCreatePayload {
  name: string;
  description?: string | null;
  permissions: string[];
}

export type RoleUpdatePayload = Partial<RoleCreatePayload>;

export const rolesApi = {
  list: async (params: ListParams = {}): Promise<Page<Role>> => {
    const { data } = await apiClient.get<Page<Role>>("/roles", { params });
    return data;
  },

  create: async (payload: RoleCreatePayload): Promise<Role> => {
    const { data } = await apiClient.post<Role>("/roles", payload);
    return data;
  },

  update: async (id: number, payload: RoleUpdatePayload): Promise<Role> => {
    const { data } = await apiClient.patch<Role>(`/roles/${id}`, payload);
    return data;
  },

  remove: async (id: number): Promise<void> => {
    await apiClient.delete(`/roles/${id}`);
  },
};
