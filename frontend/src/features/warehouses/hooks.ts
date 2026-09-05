"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { getErrorMessage } from "@/lib/api-client";
import type { StockAdjustRequest, WarehouseCreate, WarehouseUpdate } from "@/lib/api/types";
import type { ListParams } from "@/lib/types";
import { stockApi, warehousesApi } from "@/features/warehouses/api";

const WAREHOUSES_KEY = "warehouses";
const STOCK_KEY = "warehouse-stock";

export function useWarehouses(params: ListParams) {
  return useQuery({
    queryKey: [WAREHOUSES_KEY, params],
    queryFn: () => warehousesApi.list(params),
    placeholderData: keepPreviousData,
  });
}

/** Unpaginated-ish list for pickers (the stock adjust dialog's warehouse select). */
export function useAllWarehouses() {
  return useQuery({
    queryKey: [WAREHOUSES_KEY, "all"],
    queryFn: () => warehousesApi.list({ page_size: 100 }),
    staleTime: 30_000,
  });
}

export function useWarehouseStock(warehouseId: number | null) {
  return useQuery({
    queryKey: [STOCK_KEY, warehouseId],
    queryFn: () => warehousesApi.stock(warehouseId!, { page_size: 100 }),
    enabled: warehouseId != null,
    placeholderData: keepPreviousData,
  });
}

export function useCreateWarehouse() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: WarehouseCreate) => warehousesApi.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [WAREHOUSES_KEY] });
      toast.success("Warehouse created");
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}

export function useUpdateWarehouse() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: WarehouseUpdate }) =>
      warehousesApi.update(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [WAREHOUSES_KEY] });
      toast.success("Warehouse updated");
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}

export function useDeleteWarehouse() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => warehousesApi.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [WAREHOUSES_KEY] });
      toast.success("Warehouse deleted");
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}

export function useAdjustStock() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: StockAdjustRequest) => stockApi.adjust(payload),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [STOCK_KEY, variables.warehouse_id] });
      toast.success("Stock adjusted");
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}
