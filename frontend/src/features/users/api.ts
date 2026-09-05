import { apiClient } from "@/lib/api-client";
import type { ListParams, Page } from "@/lib/types";
import type { User } from "@/features/auth/types";

export interface UserListParams extends ListParams {
  role_id?: number;
  is_active?: boolean;
}

export interface UserCreatePayload {
  email: string;
  password: string;
  full_name: string;
  role_id?: number | null;
  is_active?: boolean;
}

export type UserUpdatePayload = Partial<UserCreatePayload>;

export const usersApi = {
  list: async (params: UserListParams): Promise<Page<User>> => {
    const { data } = await apiClient.get<Page<User>>("/users", { params });
    return data;
  },

  create: async (payload: UserCreatePayload): Promise<User> => {
    const { data } = await apiClient.post<User>("/users", payload);
    return data;
  },

  update: async (id: number, payload: UserUpdatePayload): Promise<User> => {
    const { data } = await apiClient.patch<User>(`/users/${id}`, payload);
    return data;
  },

  remove: async (id: number): Promise<void> => {
    await apiClient.delete(`/users/${id}`);
  },
};
