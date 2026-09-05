import { apiClient, type TokenPair } from "@/lib/api-client";
import type { LoginPayload, RegisterPayload, User } from "@/features/auth/types";

export const authApi = {
  login: async (payload: LoginPayload): Promise<TokenPair> => {
    const { data } = await apiClient.post<TokenPair>("/auth/login", payload);
    return data;
  },

  register: async (payload: RegisterPayload): Promise<User> => {
    const { data } = await apiClient.post<User>("/auth/register", payload);
    return data;
  },

  me: async (): Promise<User> => {
    const { data } = await apiClient.get<User>("/auth/me");
    return data;
  },

  updateMe: async (payload: { full_name?: string; password?: string }): Promise<User> => {
    const { data } = await apiClient.patch<User>("/auth/me", payload);
    return data;
  },
};
