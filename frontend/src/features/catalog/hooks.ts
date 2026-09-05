"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { getErrorMessage } from "@/lib/api-client";
import type { ProductCreate, ProductUpdate, ProductVariantCreate, ProductVariantUpdate } from "@/lib/api/types";
import {
  categoriesApi,
  productsApi,
  variantsApi,
  type ProductListParams,
} from "@/features/catalog/api";

const PRODUCTS_KEY = "products";
const CATEGORIES_KEY = "categories";

/** All categories, unpaginated for practical purposes — used to populate
 * dropdowns. Cached long: categories rarely change mid-session. */
export function useCategories() {
  return useQuery({
    queryKey: [CATEGORIES_KEY, "all"],
    queryFn: () => categoriesApi.list({ page_size: 100 }),
    staleTime: 5 * 60_000,
  });
}

export function useProducts(params: ProductListParams) {
  return useQuery({
    queryKey: [PRODUCTS_KEY, params],
    queryFn: () => productsApi.list(params),
    placeholderData: keepPreviousData,
  });
}

/** Unpaginated-ish product list for pickers (price list entries, etc). */
export function useAllProducts() {
  return useQuery({
    queryKey: [PRODUCTS_KEY, "all"],
    queryFn: () => productsApi.list({ page_size: 100 }),
    staleTime: 30_000,
  });
}

export function useCreateProduct() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ProductCreate) => productsApi.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PRODUCTS_KEY] });
      toast.success("Product created");
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}

export function useUpdateProduct() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: ProductUpdate }) =>
      productsApi.update(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PRODUCTS_KEY] });
      toast.success("Product updated");
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}

export function useDeleteProduct() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => productsApi.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PRODUCTS_KEY] });
      toast.success("Product deleted");
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}

export function useCreateVariant() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ productId, payload }: { productId: number; payload: ProductVariantCreate }) =>
      variantsApi.create(productId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PRODUCTS_KEY] });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}

export function useUpdateVariant() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      productId,
      variantId,
      payload,
    }: {
      productId: number;
      variantId: number;
      payload: ProductVariantUpdate;
    }) => variantsApi.update(productId, variantId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PRODUCTS_KEY] });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}

export function useDeleteVariant() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ productId, variantId }: { productId: number; variantId: number }) =>
      variantsApi.remove(productId, variantId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [PRODUCTS_KEY] });
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });
}
