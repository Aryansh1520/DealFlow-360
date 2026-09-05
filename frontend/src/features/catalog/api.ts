import { apiClient } from "@/lib/api-client";
import type {
  CategoryRead,
  ProductCreate,
  ProductRead,
  ProductUpdate,
  ProductVariantCreate,
  ProductVariantRead,
  ProductVariantUpdate,
} from "@/lib/api/types";
import type { ListParams, Page } from "@/lib/types";

export interface ProductListParams extends ListParams {
  category_id?: number;
  is_promoted?: boolean;
  line_type?: string;
  is_active?: boolean;
}

export const categoriesApi = {
  list: async (params: ListParams = {}): Promise<Page<CategoryRead>> => {
    const { data } = await apiClient.get<Page<CategoryRead>>("/categories", { params });
    return data;
  },
};

export const productsApi = {
  list: async (params: ProductListParams): Promise<Page<ProductRead>> => {
    const { data } = await apiClient.get<Page<ProductRead>>("/products", { params });
    return data;
  },

  create: async (payload: ProductCreate): Promise<ProductRead> => {
    const { data } = await apiClient.post<ProductRead>("/products", payload);
    return data;
  },

  update: async (id: number, payload: ProductUpdate): Promise<ProductRead> => {
    const { data } = await apiClient.patch<ProductRead>(`/products/${id}`, payload);
    return data;
  },

  remove: async (id: number): Promise<void> => {
    await apiClient.delete(`/products/${id}`);
  },
};

export const variantsApi = {
  create: async (
    productId: number,
    payload: ProductVariantCreate
  ): Promise<ProductVariantRead> => {
    const { data } = await apiClient.post<ProductVariantRead>(
      `/products/${productId}/variants`,
      payload
    );
    return data;
  },

  update: async (
    productId: number,
    variantId: number,
    payload: ProductVariantUpdate
  ): Promise<ProductVariantRead> => {
    const { data } = await apiClient.patch<ProductVariantRead>(
      `/products/${productId}/variants/${variantId}`,
      payload
    );
    return data;
  },

  remove: async (productId: number, variantId: number): Promise<void> => {
    await apiClient.delete(`/products/${productId}/variants/${variantId}`);
  },
};
