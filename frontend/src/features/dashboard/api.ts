import { apiClient } from "@/lib/api-client";
import type { AlertRead, DashboardSummary, DealHealthRow } from "@/lib/api/types";
import type { Page } from "@/lib/types";

export interface DealHealthParams {
  owner_rep_id?: number;
  stage?: string;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: "asc" | "desc";
}

export const dashboardApi = {
  summary: async (): Promise<{ data: DashboardSummary; elapsedMs: number }> => {
    const started = performance.now();
    const { data } = await apiClient.get<DashboardSummary>("/dashboard");
    return { data, elapsedMs: Math.round(performance.now() - started) };
  },

  dealHealth: async (
    params: DealHealthParams
  ): Promise<{ data: Page<DealHealthRow>; elapsedMs: number }> => {
    const started = performance.now();
    const { data } = await apiClient.get<Page<DealHealthRow>>("/dashboard/deal-health", { params });
    return { data, elapsedMs: Math.round(performance.now() - started) };
  },

  alerts: async (params: {
    type?: string;
    acknowledged?: boolean;
    page?: number;
    page_size?: number;
  }): Promise<Page<AlertRead>> => {
    const { data } = await apiClient.get<Page<AlertRead>>("/dashboard/alerts", { params });
    return data;
  },

  nudge: async (id: number): Promise<AlertRead> => {
    const { data } = await apiClient.post<AlertRead>(`/dashboard/alerts/${id}/nudge`);
    return data;
  },

  acknowledge: async (id: number): Promise<AlertRead> => {
    const { data } = await apiClient.post<AlertRead>(`/dashboard/alerts/${id}/acknowledge`);
    return data;
  },
};
