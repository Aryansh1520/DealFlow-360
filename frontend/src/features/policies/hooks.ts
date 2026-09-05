"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { getErrorMessage } from "@/lib/api-client";
import type { PolicyCreate } from "@/lib/api/types";
import type { ListParams } from "@/lib/types";
import { policiesApi } from "@/features/policies/api";

const POLICIES_KEY = "policies";

export function usePolicies(params: ListParams = {}) {
  return useQuery({
    queryKey: [POLICIES_KEY, params],
    queryFn: () => policiesApi.list({ page_size: 100, ...params }),
  });
}

export function useActivePolicy() {
  return useQuery({
    queryKey: [POLICIES_KEY, "active"],
    queryFn: policiesApi.active,
  });
}

export function useCreatePolicyVersion() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: PolicyCreate) => policiesApi.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [POLICIES_KEY] });
      toast.success("Draft policy version created");
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}

export function useActivatePolicy() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => policiesApi.activate(id),
    onSuccess: (policy) => {
      queryClient.invalidateQueries({ queryKey: [POLICIES_KEY] });
      toast.success(`Policy v${policy.version} activated`);
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}
