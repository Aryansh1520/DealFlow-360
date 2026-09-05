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

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  full_name: string;
}
