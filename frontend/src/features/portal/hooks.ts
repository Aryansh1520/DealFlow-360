"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { VersionConflictError, getErrorMessage } from "@/lib/api-client";
import type { ListParams } from "@/lib/types";
import {
  portalApi,
  type PortalCommentPayload,
  type PortalCounterPayload,
} from "@/features/portal/api";

const PORTAL_KEY = "portal";

export function usePortalQuotations(params: ListParams) {
  return useQuery({
    queryKey: [PORTAL_KEY, "quotations", params],
    queryFn: () => portalApi.list(params),
    placeholderData: keepPreviousData,
  });
}

export function usePortalQuotation(id: number) {
  return useQuery({
    queryKey: [PORTAL_KEY, "quotation", id],
    queryFn: () => portalApi.get(id),
    enabled: Number.isFinite(id) && id > 0,
  });
}

function onError(qc: ReturnType<typeof useQueryClient>, id: number, error: unknown) {
  if (error instanceof VersionConflictError) {
    qc.invalidateQueries({ queryKey: [PORTAL_KEY, "quotation", id] });
    toast.warning("Your rep just updated this quotation — refreshed to the latest version.");
    return;
  }
  toast.error(getErrorMessage(error));
}

export function usePortalComment(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: PortalCommentPayload) => portalApi.comment(id, payload),
    onSuccess: (quotation) => {
      qc.setQueryData([PORTAL_KEY, "quotation", id], quotation);
      toast.success("Comment sent to your rep.");
    },
    onError: (error) => onError(qc, id, error),
  });
}

export function usePortalCounter(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: PortalCounterPayload) => portalApi.counter(id, payload),
    onSuccess: (quotation) => {
      qc.setQueryData([PORTAL_KEY, "quotation", id], quotation);
      toast.success("Discount request submitted.");
    },
    onError: (error) => onError(qc, id, error),
  });
}

export function usePortalConfirm(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      expectedVersion,
      idempotencyKey,
    }: {
      expectedVersion: number;
      idempotencyKey: string;
    }) => portalApi.confirm(id, expectedVersion, idempotencyKey),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [PORTAL_KEY, "quotation", id] });
      qc.invalidateQueries({ queryKey: [PORTAL_KEY, "quotations"] });
    },
    onError: (error) => onError(qc, id, error),
  });
}

export { PORTAL_KEY };
