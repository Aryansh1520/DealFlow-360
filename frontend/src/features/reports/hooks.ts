"use client";

import { keepPreviousData, useMutation, useQuery } from "@tanstack/react-query";
import { toast } from "sonner";

import { getErrorMessage } from "@/lib/api-client";
import { reportsApi, type SalesReportFilters } from "@/features/reports/api";

export function useSalesReport(filters: SalesReportFilters) {
  return useQuery({
    queryKey: ["reports", "sales", filters],
    queryFn: () => reportsApi.sales(filters),
    placeholderData: keepPreviousData,
  });
}

export function useExportReport(filters: SalesReportFilters) {
  return useMutation({
    mutationFn: (format: "pdf" | "xlsx") => reportsApi.export(format, filters),
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}
