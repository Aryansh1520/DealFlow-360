/** Shared API types matching the backend's response envelopes. */

/** The two top-level identities in the system — see `features/auth/auth-context.tsx`. */
export type UserType = "internal" | "customer";

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ListParams {
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: "asc" | "desc";
  search?: string;
}
