import type { UserType } from "@/lib/types";

export type { UserType };

export interface Role {
  id: number;
  name: string;
  description: string | null;
  permissions: string[];
}

export interface User {
  id: number;
  email: string;
  full_name: string;
  is_active: boolean;
  role: Role | null;
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
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  full_name: string;
}
