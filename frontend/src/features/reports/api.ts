import { apiClient } from "@/lib/api-client";
import type { SalesReportRow } from "@/lib/api/types";
import type { Page } from "@/lib/types";

export interface SalesReportFilters {
  period?: string; // "YYYY-MM"
  rep_id?: number;
  team_id?: number;
  approval_status?: string;
  category_id?: number;
}

export const reportsApi = {
  sales: async (
    filters: SalesReportFilters,
    page = 1
  ): Promise<Page<SalesReportRow>> => {
    const { data } = await apiClient.get<Page<SalesReportRow>>("/reports/sales", {
      params: { ...filters, page, page_size: 100 },
    });
    return data;
  },

  /** Downloads via a blob so the `Authorization` header is sent — a plain
   * `<a href>` would 401. */
  export: async (format: "pdf" | "xlsx", filters: SalesReportFilters): Promise<void> => {
    const response = await apiClient.get("/reports/sales/export", {
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
    a.download = `sales-report.${format === "pdf" ? "pdf" : "xlsx"}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  },
};
