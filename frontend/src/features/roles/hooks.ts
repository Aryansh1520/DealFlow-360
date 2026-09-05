"use client";

import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { toast } from "sonner";

import { getErrorMessage } from "@/lib/api-client";
import type { ListParams } from "@/lib/types";
import {
  rolesApi,
  type RoleCreatePayload,
  type RoleUpdatePayload,
} from "@/features/roles/api";

const ROLES_KEY = "roles";

export function useRoles(params: ListParams = { page_size: 100 }) {
  return useQuery({
    queryKey: [ROLES_KEY, params],
    queryFn: () => rolesApi.list(params),
    placeholderData: keepPreviousData,
  });
}

export function useCreateRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: RoleCreatePayload) => rolesApi.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [ROLES_KEY] });
      toast.success("Role created");
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}

export function useUpdateRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: RoleUpdatePayload }) =>
      rolesApi.update(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [ROLES_KEY] });
      toast.success("Role updated");
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}

export function useDeleteRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => rolesApi.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [ROLES_KEY] });
      toast.success("Role deleted");
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}
