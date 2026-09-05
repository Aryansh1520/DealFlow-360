import { apiClient } from "@/lib/api-client";
import type { AlertRead, DashboardSummary, DealHealthRow } from "@/lib/api/types";
import type { Page } from "@/lib/types";

export interface DealHealthParams {
  owner_rep_id?: number;
  stage?: string;
  /** ISO 8601 — only rows active on/after this instant. */
  active_since?: string;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: "asc" | "desc";
}

export interface DealHealthExportFilters {
  owner_rep_id?: number;
  stage?: string;
  active_since?: string;
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

  /** Streams a pdf / xlsx of the whole filtered deal-health set (server walks every
   * page), regardless of any client-side pagination. Blob download so the auth
   * header is sent — a plain `<a href>` would 401. Mirrors `reportsApi.export`. */
  exportDealHealth: async (
    format: "pdf" | "xlsx",
    filters: DealHealthExportFilters
  ): Promise<void> => {
    const response = await apiClient.get("/dashboard/deal-health/export", {
      params: { format, ...filters },
      responseType: "blob",
    });
    const mime =
      format === "pdf"
        ? "application/pdf"
        : "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
    const blob = new Blob([response.data as BlobPart], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `deal-health.${format === "pdf" ? "pdf" : "xlsx"}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
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
