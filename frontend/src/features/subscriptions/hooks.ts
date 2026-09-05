"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { getErrorMessage } from "@/lib/api-client";
import type { SubscriptionPlanCreate, SubscriptionPlanUpdate } from "@/lib/api/types";
import type { ListParams } from "@/lib/types";
import { subscriptionPlansApi } from "@/features/subscriptions/api";

const PLANS_KEY = "subscription-plans";

export function useSubscriptionPlans(params: ListParams) {
  return useQuery({
    queryKey: [PLANS_KEY, params],
    queryFn: () => subscriptionPlansApi.list(params),
    placeholderData: keepPreviousData,
  });
}

/** Unpaginated-ish list for pickers (the product form's plan select). */
export function useAllSubscriptionPlans() {
  return useQuery({
    queryKey: [PLANS_KEY, "all"],
    queryFn: () => subscriptionPlansApi.list({ page_size: 100 }),
    staleTime: 30_000,
  });
}

export function useCreateSubscriptionPlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: SubscriptionPlanCreate) => subscriptionPlansApi.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PLANS_KEY] });
      toast.success("Plan created");
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}

export function useUpdateSubscriptionPlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: SubscriptionPlanUpdate }) =>
      subscriptionPlansApi.update(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PLANS_KEY] });
      toast.success("Plan updated");
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}

export function useDeleteSubscriptionPlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => subscriptionPlansApi.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PLANS_KEY] });
      toast.success("Plan deleted");
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}
