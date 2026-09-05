"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { getErrorMessage } from "@/lib/api-client";
import {
  dashboardApi,
  type DealHealthExportFilters,
  type DealHealthParams,
} from "@/features/dashboard/api";

const DASHBOARD_KEY = "dashboard";

export function useDashboardSummary() {
  return useQuery({
    queryKey: [DASHBOARD_KEY, "summary"],
    queryFn: dashboardApi.summary,
    staleTime: 15_000,
  });
}

export function useDealHealth(params: DealHealthParams) {
  return useQuery({
    queryKey: [DASHBOARD_KEY, "deal-health", params],
    queryFn: () => dashboardApi.dealHealth(params),
    placeholderData: keepPreviousData,
  });
}

export function useExportDealHealth(filters: DealHealthExportFilters) {
  return useMutation({
    mutationFn: (format: "pdf" | "xlsx") => dashboardApi.exportDealHealth(format, filters),
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}

export function useAlerts(params: { type?: string; acknowledged?: boolean }) {
  return useQuery({
    queryKey: [DASHBOARD_KEY, "alerts", params],
    queryFn: () => dashboardApi.alerts({ ...params, page_size: 100 }),
  });
}

export function useNudgeAlert() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => dashboardApi.nudge(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [DASHBOARD_KEY] });
      toast.success("Owner nudged");
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}

export function useAcknowledgeAlert() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => dashboardApi.acknowledge(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [DASHBOARD_KEY] });
      toast.success("Alert acknowledged");
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}

export { DASHBOARD_KEY };
