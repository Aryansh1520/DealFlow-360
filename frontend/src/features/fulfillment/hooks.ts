"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import {
  InsufficientStockError,
  IllegalTransitionError,
  VersionConflictError,
  getErrorMessage,
} from "@/lib/api-client";
import type { AllocationInput } from "@/lib/api/types";
import { QUOTATIONS_KEY } from "@/features/quotations/hooks";
import { fulfillmentApi } from "@/features/fulfillment/api";

const FULFILLMENT_KEY = "fulfillment";

export function useFulfillmentPlan(quotationId: number) {
  return useQuery({
    queryKey: [FULFILLMENT_KEY, quotationId, "plan"],
    queryFn: () => fulfillmentApi.plan(quotationId),
    enabled: Number.isFinite(quotationId) && quotationId > 0,
  });
}

function useSharedSuccess(quotationId: number) {
  const qc = useQueryClient();
  return (msg: string) => {
    qc.invalidateQueries({ queryKey: [FULFILLMENT_KEY, quotationId] });
    qc.invalidateQueries({ queryKey: [QUOTATIONS_KEY, quotationId] });
    qc.invalidateQueries({ queryKey: [QUOTATIONS_KEY, quotationId, "events"] });
    toast.success(msg);
  };
}

function handleFulfillmentError(qc: ReturnType<typeof useQueryClient>, quotationId: number, error: unknown) {
  if (error instanceof VersionConflictError) {
    qc.setQueryData([QUOTATIONS_KEY, quotationId], error.current);
    toast.warning("This quote changed — refreshed to the latest version.");
    return;
  }
  if (error instanceof IllegalTransitionError) {
    // Stale plan hash — the plan moved under us.
    qc.invalidateQueries({ queryKey: [FULFILLMENT_KEY, quotationId] });
    toast.warning("Stock changed — here's the updated split.");
    return;
  }
  if (error instanceof InsufficientStockError) {
    // The dialog surfaces `error.data.shortfalls`; still toast the headline.
    toast.error(error.message);
    return;
  }
  toast.error(getErrorMessage(error));
}

export function useAcceptPlan(quotationId: number) {
  const qc = useQueryClient();
  const onSuccess = useSharedSuccess(quotationId);
  return useMutation({
    mutationFn: ({
      expectedVersion,
      planHash,
      idempotencyKey,
    }: {
      expectedVersion: number;
      planHash: string;
      idempotencyKey: string;
    }) =>
      fulfillmentApi.accept(
        quotationId,
        { expected_version: expectedVersion, plan_hash: planHash },
        idempotencyKey
      ),
    onSuccess: () => onSuccess("Split accepted — stock reserved."),
    onError: (error) => handleFulfillmentError(qc, quotationId, error),
  });
}

export function useOverridePlan(quotationId: number) {
  const qc = useQueryClient();
  const onSuccess = useSharedSuccess(quotationId);
  return useMutation({
    mutationFn: ({
      expectedVersion,
      allocations,
      idempotencyKey,
    }: {
      expectedVersion: number;
      allocations: AllocationInput[];
      idempotencyKey: string;
    }) =>
      fulfillmentApi.override(
        quotationId,
        { expected_version: expectedVersion, allocations },
        idempotencyKey
      ),
    onSuccess: () => onSuccess("Manual allocation saved."),
    onError: (error) => handleFulfillmentError(qc, quotationId, error),
  });
}

export function useConsolidateBackorders(quotationId: number) {
  const qc = useQueryClient();
  const onSuccess = useSharedSuccess(quotationId);
  return useMutation({
    mutationFn: ({
      expectedVersion,
      idempotencyKey,
    }: {
      expectedVersion: number;
      idempotencyKey: string;
    }) =>
      fulfillmentApi.consolidate(
        quotationId,
        { expected_version: expectedVersion },
        idempotencyKey
      ),
    onSuccess: () => onSuccess("Backorders consolidated into a new shipment."),
    onError: (error) => handleFulfillmentError(qc, quotationId, error),
  });
}

export { FULFILLMENT_KEY };
