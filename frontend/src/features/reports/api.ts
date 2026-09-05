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
  /** Pulls up to `pageSize` rows (the backend caps this at 100); the table
   * paginates that slice client-side so the summary total and the revenue-by-rep
   * chart stay accurate for what's loaded. When `total` exceeds what came back,
   * the screen shows a "narrow the filters or export" notice. Exports go through
   * `/reports/sales/export`, which walks every page server-side — pagination here
   * never limits a download. */
  sales: async (
    filters: SalesReportFilters,
    page = 1,
    pageSize = 100
  ): Promise<Page<SalesReportRow>> => {
    const { data } = await apiClient.get<Page<SalesReportRow>>("/reports/sales", {
      params: { ...filters, page, page_size: pageSize },
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
