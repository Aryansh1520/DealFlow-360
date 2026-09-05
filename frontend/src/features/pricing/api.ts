import { apiClient } from "@/lib/api-client";
import type {
  PriceListCreate,
  PriceListEntryCreate,
  PriceListEntryRead,
  PriceListEntryUpdate,
  PriceListRead,
  PriceListUpdate,
} from "@/lib/api/types";
import type { ListParams, Page } from "@/lib/types";

export const priceListsApi = {
  list: async (params: ListParams): Promise<Page<PriceListRead>> => {
    const { data } = await apiClient.get<Page<PriceListRead>>("/price-lists", { params });
    return data;
  },

  create: async (payload: PriceListCreate): Promise<PriceListRead> => {
    const { data } = await apiClient.post<PriceListRead>("/price-lists", payload);
    return data;
  },

  update: async (id: number, payload: PriceListUpdate): Promise<PriceListRead> => {
    const { data } = await apiClient.patch<PriceListRead>(`/price-lists/${id}`, payload);
    return data;
  },

  remove: async (id: number): Promise<void> => {
    await apiClient.delete(`/price-lists/${id}`);
  },
};

export const priceListEntriesApi = {
  list: async (priceListId: number, params: ListParams = {}): Promise<Page<PriceListEntryRead>> => {
    const { data } = await apiClient.get<Page<PriceListEntryRead>>(
      `/price-lists/${priceListId}/entries`,
      { params }
    );
    return data;
  },

  create: async (
    priceListId: number,
    payload: PriceListEntryCreate
  ): Promise<PriceListEntryRead> => {
    const { data } = await apiClient.post<PriceListEntryRead>(
      `/price-lists/${priceListId}/entries`,
      payload
    );
    return data;
  },

  update: async (
    priceListId: number,
    entryId: number,
    payload: PriceListEntryUpdate
  ): Promise<PriceListEntryRead> => {
    const { data } = await apiClient.patch<PriceListEntryRead>(
      `/price-lists/${priceListId}/entries/${entryId}`,
      payload
    );
    return data;
  },

  remove: async (priceListId: number, entryId: number): Promise<void> => {
    await apiClient.delete(`/price-lists/${priceListId}/entries/${entryId}`);
  },
};
