"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { getErrorMessage } from "@/lib/api-client";
import type {
  PriceListCreate,
  PriceListEntryCreate,
  PriceListEntryUpdate,
  PriceListUpdate,
} from "@/lib/api/types";
import type { ListParams } from "@/lib/types";
import { priceListEntriesApi, priceListsApi } from "@/features/pricing/api";

const PRICE_LISTS_KEY = "price-lists";
const ENTRIES_KEY = "price-list-entries";

export function usePriceLists(params: ListParams) {
  return useQuery({
    queryKey: [PRICE_LISTS_KEY, params],
    queryFn: () => priceListsApi.list(params),
    placeholderData: keepPreviousData,
  });
}

export function useCreatePriceList() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: PriceListCreate) => priceListsApi.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PRICE_LISTS_KEY] });
      toast.success("Price list created");
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}

export function useUpdatePriceList() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: PriceListUpdate }) =>
      priceListsApi.update(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PRICE_LISTS_KEY] });
      toast.success("Price list updated");
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}

export function useDeletePriceList() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => priceListsApi.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PRICE_LISTS_KEY] });
      toast.success("Price list deleted");
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}

export function usePriceListEntries(priceListId: number | null) {
  return useQuery({
    queryKey: [ENTRIES_KEY, priceListId],
    queryFn: () => priceListEntriesApi.list(priceListId!, { page_size: 100 }),
    enabled: priceListId != null,
    placeholderData: keepPreviousData,
  });
}

export function useCreatePriceListEntry() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      priceListId,
      payload,
    }: {
      priceListId: number;
      payload: PriceListEntryCreate;
    }) => priceListEntriesApi.create(priceListId, payload),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [ENTRIES_KEY, variables.priceListId] });
      toast.success("Entry added");
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}

export function useUpdatePriceListEntry() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      priceListId,
      entryId,
      payload,
    }: {
      priceListId: number;
      entryId: number;
      payload: PriceListEntryUpdate;
    }) => priceListEntriesApi.update(priceListId, entryId, payload),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [ENTRIES_KEY, variables.priceListId] });
      toast.success("Entry updated");
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}

export function useDeletePriceListEntry() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ priceListId, entryId }: { priceListId: number; entryId: number }) =>
      priceListEntriesApi.remove(priceListId, entryId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [ENTRIES_KEY, variables.priceListId] });
      toast.success("Entry removed");
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}
