"use client";

import { keepPreviousData, useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { VersionConflictError, getErrorMessage } from "@/lib/api-client";
import type { QuotationRead } from "@/lib/api/types";
import { useAuth } from "@/features/auth/auth-context";
import {
  quotationsApi,
  type AddLinePayload,
  type QuotationCreatePayload,
  type QuotationListParams,
  type UpdateLinePayload,
} from "@/features/quotations/api";

const QUOTATIONS_KEY = "quotations";
const EVENTS_PAGE_SIZE = 20;

function useActor() {
  const { user } = useAuth();
  return { id: user?.id ?? 0, name: user?.full_name ?? "Unknown" };
}

export function useQuotations(params: QuotationListParams) {
  return useQuery({
    queryKey: [QUOTATIONS_KEY, params],
    queryFn: () => quotationsApi.list(params),
    placeholderData: keepPreviousData,
  });
}

export function useQuotation(id: number) {
  return useQuery({
    queryKey: [QUOTATIONS_KEY, id],
    queryFn: () => quotationsApi.get(id),
  });
}

/** Shared conflict handling for every quotation mutation — contract §7:
 * replace the cache with the server's current truth, toast, never auto-retry. */
function onVersionConflict(queryClient: ReturnType<typeof useQueryClient>, id: number, error: unknown) {
  if (error instanceof VersionConflictError) {
    queryClient.setQueryData([QUOTATIONS_KEY, id], error.current);
    toast.warning("This quote changed — refreshed to the latest version.");
    return true;
  }
  return false;
}

export function useCreateQuotation() {
  const queryClient = useQueryClient();
  const actor = useActor();
  return useMutation({
    mutationFn: (payload: QuotationCreatePayload) => quotationsApi.create(payload, actor),
    onSuccess: (quotation) => {
      queryClient.invalidateQueries({ queryKey: [QUOTATIONS_KEY] });
      queryClient.setQueryData([QUOTATIONS_KEY, quotation.id], quotation);
      toast.success(`${quotation.reference} created`);
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}

export function useAddLine(id: number) {
  const queryClient = useQueryClient();
  const actor = useActor();
  return useMutation({
    mutationFn: (payload: AddLinePayload) => quotationsApi.addLine(id, payload, actor),
    onSuccess: (quotation) => {
      queryClient.setQueryData([QUOTATIONS_KEY, id], quotation);
      queryClient.invalidateQueries({ queryKey: [QUOTATIONS_KEY, id, "events"] });
    },
    onError: (error) => {
      if (!onVersionConflict(queryClient, id, error)) toast.error(getErrorMessage(error));
    },
  });
}

export function useUpdateLine(id: number) {
  const queryClient = useQueryClient();
  const actor = useActor();
  return useMutation({
    mutationFn: ({ lineId, payload }: { lineId: number; payload: UpdateLinePayload }) =>
      quotationsApi.updateLine(id, lineId, payload, actor),
    onSuccess: (quotation) => {
      queryClient.setQueryData([QUOTATIONS_KEY, id], quotation);
      queryClient.invalidateQueries({ queryKey: [QUOTATIONS_KEY, id, "events"] });
    },
    onError: (error) => {
      if (!onVersionConflict(queryClient, id, error)) toast.error(getErrorMessage(error));
    },
  });
}

export function useRemoveLine(id: number) {
  const queryClient = useQueryClient();
  const actor = useActor();
  return useMutation({
    mutationFn: ({ lineId, expectedVersion }: { lineId: number; expectedVersion: number }) =>
      quotationsApi.removeLine(id, lineId, expectedVersion, actor),
    onSuccess: (quotation) => {
      queryClient.setQueryData([QUOTATIONS_KEY, id], quotation);
      queryClient.invalidateQueries({ queryKey: [QUOTATIONS_KEY, id, "events"] });
    },
    onError: (error) => {
      if (!onVersionConflict(queryClient, id, error)) toast.error(getErrorMessage(error));
    },
  });
}

export function useSubmitQuotation(id: number) {
  const queryClient = useQueryClient();
  const actor = useActor();
  return useMutation({
    mutationFn: ({ expectedVersion, idempotencyKey }: { expectedVersion: number; idempotencyKey: string }) =>
      quotationsApi.submit(id, { expected_version: expectedVersion }, idempotencyKey, actor),
    onSuccess: (quotation) => {
      queryClient.setQueryData([QUOTATIONS_KEY, id], quotation);
      queryClient.invalidateQueries({ queryKey: [QUOTATIONS_KEY, id, "events"] });
      queryClient.invalidateQueries({ queryKey: [QUOTATIONS_KEY] });
      toast.success(
        quotation.computation.required_approvals.length > 0
          ? "Submitted for approval"
          : "Auto-approved — no policy breach"
      );
    },
    onError: (error) => {
      if (!onVersionConflict(queryClient, id, error)) toast.error(getErrorMessage(error));
    },
  });
}

export function useTransitionQuotation(id: number) {
  const queryClient = useQueryClient();
  const actor = useActor();
  return useMutation({
    mutationFn: ({
      toStatus,
      expectedVersion,
      reason,
      idempotencyKey,
    }: {
      toStatus: string;
      expectedVersion: number;
      reason?: string;
      idempotencyKey: string;
    }) =>
      quotationsApi.transition(
        id,
        { expected_version: expectedVersion, to_status: toStatus, reason },
        idempotencyKey,
        actor
      ),
    onSuccess: (quotation: QuotationRead) => {
      queryClient.setQueryData([QUOTATIONS_KEY, id], quotation);
      queryClient.invalidateQueries({ queryKey: [QUOTATIONS_KEY, id, "events"] });
      queryClient.invalidateQueries({ queryKey: [QUOTATIONS_KEY] });
    },
    onError: (error) => {
      if (!onVersionConflict(queryClient, id, error)) toast.error(getErrorMessage(error));
    },
  });
}

export function useQuotationEvents(id: number) {
  return useInfiniteQuery({
    queryKey: [QUOTATIONS_KEY, id, "events"],
    queryFn: ({ pageParam }) =>
      quotationsApi.events(id, { page: pageParam, page_size: EVENTS_PAGE_SIZE }),
    initialPageParam: 1,
    getNextPageParam: (lastPage) => (lastPage.page < lastPage.pages ? lastPage.page + 1 : undefined),
  });
}

export function useDecisionTrace(id: number, enabled = true) {
  return useQuery({
    queryKey: [QUOTATIONS_KEY, id, "decision-trace"],
    queryFn: () => quotationsApi.decisionTrace(id),
    enabled,
  });
}

export function useSuggestions(id: number) {
  return useQuery({
    queryKey: [QUOTATIONS_KEY, id, "suggestions"],
    queryFn: () => quotationsApi.suggestions(id),
  });
}

export function useDismissSuggestion(id: number) {
  const queryClient = useQueryClient();
  const actor = useActor();
  return useMutation({
    mutationFn: (productId: number) => quotationsApi.dismissSuggestion(id, productId, actor),
    onMutate: async (productId) => {
      await queryClient.cancelQueries({ queryKey: [QUOTATIONS_KEY, id, "suggestions"] });
      const previous = queryClient.getQueryData([QUOTATIONS_KEY, id, "suggestions"]);
      queryClient.setQueryData(
        [QUOTATIONS_KEY, id, "suggestions"],
        (current: Awaited<ReturnType<typeof quotationsApi.suggestions>> | undefined) =>
          current?.filter((s) => s.product_id !== productId) ?? []
      );
      return { previous };
    },
    onError: (error, _productId, context) => {
      if (context?.previous) {
        queryClient.setQueryData([QUOTATIONS_KEY, id, "suggestions"], context.previous);
      }
      toast.error(getErrorMessage(error));
    },
  });
}

export { QUOTATIONS_KEY };
