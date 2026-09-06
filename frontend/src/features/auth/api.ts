import { apiClient, type TokenPair } from "@/lib/api-client";
import type {
  ForgotPasswordPayload,
  ForgotPasswordResult,
  LoginPayload,
  Me,
  RegisterPayload,
  ResetPasswordPayload,
  User,
} from "@/features/auth/types";

export const authApi = {
  login: async (payload: LoginPayload): Promise<TokenPair> => {
    const { data } = await apiClient.post<TokenPair>("/auth/login", payload);
    return data;
  },

  register: async (payload: RegisterPayload): Promise<User> => {
    const { data } = await apiClient.post<User>("/auth/register", payload);
    return data;
  },

  forgotPassword: async (
    payload: ForgotPasswordPayload,
  ): Promise<ForgotPasswordResult> => {
    const { data } = await apiClient.post<ForgotPasswordResult>(
      "/auth/forgot-password",
      payload,
    );
    return data;
  },

  resetPassword: async (payload: ResetPasswordPayload): Promise<void> => {
    await apiClient.post("/auth/reset-password", payload);
  },

  me: async (): Promise<Me> => {
    const { data } = await apiClient.get<Me>("/auth/me");
    return data;
  },

  updateMe: async (payload: { full_name?: string; password?: string }): Promise<User> => {
    const { data } = await apiClient.patch<User>("/auth/me", payload);
    return data;
  },
};
