"use client";

import * as React from "react";
import { keepPreviousData, useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { VersionConflictError, getErrorMessage } from "@/lib/api-client";
import type { QuotationRead, QuoteEventRead } from "@/lib/api/types";
import {
  quotationsApi,
  type AddLinePayload,
  type QuotationCreatePayload,
  type QuotationListParams,
  type UpdateLinePayload,
} from "@/features/quotations/api";

const QUOTATIONS_KEY = "quotations";
const EVENTS_PAGE_SIZE = 20;

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
  return useMutation({
    mutationFn: (payload: QuotationCreatePayload) => quotationsApi.create(payload),
    onSuccess: (quotation) => {
      queryClient.invalidateQueries({ queryKey: [QUOTATIONS_KEY] });
      queryClient.setQueryData([QUOTATIONS_KEY, quotation.id], quotation);
      toast.success(`${quotation.reference} created`);
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}

export function useUpdateQuotation(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      expected_version: number;
      order_discount_bps?: number;
      valid_until?: string | null;
    }) => quotationsApi.update(id, payload),
    onSuccess: (quotation) => {
      queryClient.setQueryData([QUOTATIONS_KEY, id], quotation);
      queryClient.invalidateQueries({ queryKey: [QUOTATIONS_KEY, id, "events"] });
      queryClient.invalidateQueries({ queryKey: [QUOTATIONS_KEY] });
    },
    onError: (error) => {
      if (!onVersionConflict(queryClient, id, error)) toast.error(getErrorMessage(error));
    },
  });
}

/** Rep declines the customer's counter-offer — records `quote.counter_rejected`
 * (visible in the portal timeline) and keeps the current terms. */
export function useRejectCounter(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { expected_version: number; reason?: string }) =>
      quotationsApi.rejectCounter(id, payload),
    onSuccess: (quotation) => {
      queryClient.setQueryData([QUOTATIONS_KEY, id], quotation);
      queryClient.invalidateQueries({ queryKey: [QUOTATIONS_KEY, id, "events"] });
      queryClient.invalidateQueries({ queryKey: [QUOTATIONS_KEY] });
      toast.success("Counter-offer declined — the customer has been notified.");
    },
    onError: (error) => {
      if (!onVersionConflict(queryClient, id, error)) toast.error(getErrorMessage(error));
    },
  });
}

export function useAddLine(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: AddLinePayload) => quotationsApi.addLine(id, payload),
    onSuccess: (quotation) => {
      queryClient.setQueryData([QUOTATIONS_KEY, id], quotation);
      queryClient.invalidateQueries({ queryKey: [QUOTATIONS_KEY, id, "events"] });
      // Suggestions are scored against the current cart (excludes what's already
      // on it, margin-deltas computed relative to it) — stale the moment a line changes.
      queryClient.invalidateQueries({ queryKey: [QUOTATIONS_KEY, id, "suggestions"] });
    },
    onError: (error) => {
      if (!onVersionConflict(queryClient, id, error)) toast.error(getErrorMessage(error));
    },
  });
}

export function useUpdateLine(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ lineId, payload }: { lineId: number; payload: UpdateLinePayload }) =>
      quotationsApi.updateLine(id, lineId, payload),
    onSuccess: (quotation) => {
      queryClient.setQueryData([QUOTATIONS_KEY, id], quotation);
      queryClient.invalidateQueries({ queryKey: [QUOTATIONS_KEY, id, "events"] });
      queryClient.invalidateQueries({ queryKey: [QUOTATIONS_KEY, id, "suggestions"] });
    },
    onError: (error) => {
      if (!onVersionConflict(queryClient, id, error)) toast.error(getErrorMessage(error));
    },
  });
}

export function useRemoveLine(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ lineId, expectedVersion }: { lineId: number; expectedVersion: number }) =>
      quotationsApi.removeLine(id, lineId, expectedVersion),
    onSuccess: (quotation) => {
      queryClient.setQueryData([QUOTATIONS_KEY, id], quotation);
      queryClient.invalidateQueries({ queryKey: [QUOTATIONS_KEY, id, "events"] });
      queryClient.invalidateQueries({ queryKey: [QUOTATIONS_KEY, id, "suggestions"] });
    },
    onError: (error) => {
      if (!onVersionConflict(queryClient, id, error)) toast.error(getErrorMessage(error));
    },
  });
}

export function useSubmitQuotation(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ expectedVersion, idempotencyKey }: { expectedVersion: number; idempotencyKey: string }) =>
      quotationsApi.submit(id, { expected_version: expectedVersion }, idempotencyKey),
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
        idempotencyKey
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

// A rep "responds" to a counter by changing a discount / line, or by declining it.
const COUNTER_RESPONDED = new Set([
  "quote.discount_changed",
  "quote.line_added",
  "quote.line_updated",
  "quote.line_removed",
  "quote.counter_rejected",
]);

export interface PendingCounter {
  event: QuoteEventRead;
  /** The discount the customer asked for, in basis points. */
  requestedBps: number;
  message: string | null;
  lineScoped: boolean;
}

/** The customer's most recent counter-offer that the rep hasn't responded to yet.
 * `null` when there is no open counter. Shared by the builder banner and the
 * order-discount cap so both agree on what "requested" means. */
export function usePendingCounter(id: number): PendingCounter | null {
  const { data } = useQuotationEvents(id);
  return React.useMemo(() => {
    const events = (data?.pages ?? []).flatMap((p) => p.items);
    const countered = events.find((e) => e.event_type === "quote.customer_countered");
    if (!countered) return null;
    const responded = events.some(
      (e) => COUNTER_RESPONDED.has(e.event_type) && e.created_at > countered.created_at
    );
    if (responded) return null;
    return {
      event: countered,
      requestedBps: Number(countered.payload?.requested_discount_bps ?? 0),
      message: (countered.payload?.message as string | undefined) ?? null,
      lineScoped: countered.payload?.line_id != null,
    };
  }, [data]);
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
  return useMutation({
    mutationFn: (productId: number) => quotationsApi.dismissSuggestion(id, productId),
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
