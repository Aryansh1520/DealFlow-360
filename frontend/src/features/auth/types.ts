import type { UserType } from "@/lib/types";

export type { UserType };

export type DashboardType = "super_admin" | "sales_manager" | "finance_ops" | "generic";

export interface Role {
  id: number;
  name: string;
  description: string | null;
  permissions: string[];
  /** Which of the four dashboard layouts the frontend renders for this role. */
  dashboard_type: DashboardType;
}

export interface User {
  id: number;
  email: string;
  full_name: string;
  is_active: boolean;
  /** The user who registered the organization. Cannot be deleted or demoted. */
  is_org_owner: boolean;
  role: Role | null;
  created_at: string;
}

/** The tenant a principal (internal user or customer) belongs to. */
export interface Organization {
  id: number;
  name: string;
  slug: string;
  created_at: string;
}

export type CustomerTier = "bronze" | "silver" | "gold";

export interface Customer {
  id: number;
  name: string;
  email: string;
  company: string | null;
  phone: string | null;
  tier: CustomerTier;
  portal_enabled: boolean;
  created_at: string;
}

/** `/auth/me` response — discriminated on `user_type`; the other profile is null. */
export interface Me {
  user_type: UserType;
  internal: User | null;
  customer: Customer | null;
  organization: Organization | null;
}

export interface LoginPayload {
  email: string;
  password: string;
}

/** Signup creates a new organization and its super admin — never a member or
 * customer of an existing organization. */
export interface RegisterPayload {
  organization_name: string;
  email: string;
  password: string;
  full_name: string;
}
