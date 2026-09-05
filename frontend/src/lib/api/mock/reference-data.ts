/**
 * Real data the mock quotation layer runs against — products, the active
 * policy and customers all come from the live, already-shipped Phase 1
 * backend. Only quotations/lines/events/approvals are mocked (see
 * `mock/store.ts`); this file is what keeps the engine's numbers honest
 * instead of inventing catalogue data too.
 */
import { categoriesApi, productsApi } from "@/features/catalog/api";
import { customersApi } from "@/features/customers/api";
import { policiesApi } from "@/features/policies/api";
import type { CategoryRead, CustomerRead, PolicyRead, ProductRead } from "@/lib/api/types";

let productsCache: ProductRead[] | null = null;
let categoriesCache: CategoryRead[] | null = null;
let policyCache: PolicyRead | null = null;
let customersCache: CustomerRead[] | null = null;

export async function getAllProducts(): Promise<ProductRead[]> {
  if (!productsCache) {
    const page = await productsApi.list({ page_size: 100 });
    productsCache = page.items;
  }
  return productsCache;
}

export async function getAllCategories(): Promise<CategoryRead[]> {
  if (!categoriesCache) {
    const page = await categoriesApi.list({ page_size: 100 });
    categoriesCache = page.items;
  }
  return categoriesCache;
}

export async function getActivePolicy(): Promise<PolicyRead> {
  if (!policyCache) {
    policyCache = await policiesApi.active();
  }
  return policyCache;
}

export async function getAllCustomers(): Promise<CustomerRead[]> {
  if (!customersCache) {
    const page = await customersApi.list({ page_size: 100 });
    customersCache = page.items;
  }
  return customersCache;
}

export async function getProduct(id: number): Promise<ProductRead> {
  const products = await getAllProducts();
  const product = products.find((p) => p.id === id);
  if (!product) throw new Error(`Mock reference data: unknown product ${id}`);
  return product;
}

export async function getCustomer(id: number): Promise<CustomerRead> {
  const customers = await getAllCustomers();
  const customer = customers.find((c) => c.id === id);
  if (!customer) throw new Error(`Mock reference data: unknown customer ${id}`);
  return customer;
}
