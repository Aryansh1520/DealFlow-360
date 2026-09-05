import { apiClient } from "@/lib/api-client";
import type {
  StockAdjustRequest,
  StockRead,
  WarehouseCreate,
  WarehouseRead,
  WarehouseUpdate,
} from "@/lib/api/types";
import type { ListParams, Page } from "@/lib/types";

export const warehousesApi = {
  list: async (params: ListParams): Promise<Page<WarehouseRead>> => {
    const { data } = await apiClient.get<Page<WarehouseRead>>("/warehouses", { params });
    return data;
  },

  create: async (payload: WarehouseCreate): Promise<WarehouseRead> => {
    const { data } = await apiClient.post<WarehouseRead>("/warehouses", payload);
    return data;
  },

  update: async (id: number, payload: WarehouseUpdate): Promise<WarehouseRead> => {
    const { data } = await apiClient.patch<WarehouseRead>(`/warehouses/${id}`, payload);
    return data;
  },

  remove: async (id: number): Promise<void> => {
    await apiClient.delete(`/warehouses/${id}`);
  },

  stock: async (id: number, params: ListParams = {}): Promise<Page<StockRead>> => {
    const { data } = await apiClient.get<Page<StockRead>>(`/warehouses/${id}/stock`, { params });
    return data;
  },
};

export const stockApi = {
  adjust: async (payload: StockAdjustRequest): Promise<StockRead> => {
    const { data } = await apiClient.post<StockRead>("/stock/adjust", payload);
    return data;
  },
};
