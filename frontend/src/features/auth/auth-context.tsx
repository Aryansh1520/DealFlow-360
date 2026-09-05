"use client";

import * as React from "react";
import { useRouter } from "next/navigation";

import { tokenStorage } from "@/lib/api-client";
import type { UserType } from "@/lib/types";
import { authApi } from "@/features/auth/api";
import type { Customer, LoginPayload, Me, RegisterPayload, User } from "@/features/auth/types";

/** Where a session of this type lands after login / on the home route. */
export function homePathFor(userType: UserType | null): string {
  return userType === "customer" ? "/portal" : "/dashboard";
}

interface AuthContextValue {
  /** Set when signed in as internal staff; null otherwise (including customer sessions). */
  user: User | null;
  /** Set when signed in as a customer; null otherwise. */
  customer: Customer | null;
  userType: UserType | null;
  isAuthenticated: boolean;
  /** True while the initial session restore is in flight. */
  isLoading: boolean;
  login: (payload: LoginPayload) => Promise<Me>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => void;
  /** True when the signed-in internal user's role grants every listed permission
   * ("*" grants all). Always false for customer sessions — they hold no permissions. */
  hasPermission: (...permissions: string[]) => boolean;
  refreshUser: () => Promise<void>;
}

const AuthContext = React.createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [me, setMe] = React.useState<Me | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);

  React.useEffect(() => {
    if (!tokenStorage.getAccess()) {
      setIsLoading(false);
      return;
    }
    authApi
      .me()
      .then(setMe)
      .catch(() => tokenStorage.clear())
      .finally(() => setIsLoading(false));
  }, []);

  const login = React.useCallback(async (payload: LoginPayload) => {
    const tokens = await authApi.login(payload);
    tokenStorage.set(tokens);
    const freshMe = await authApi.me();
    setMe(freshMe);
    return freshMe;
  }, []);

  const register = React.useCallback(
    async (payload: RegisterPayload) => {
      await authApi.register(payload);
      await login({ email: payload.email, password: payload.password });
    },
    [login]
  );

  const logout = React.useCallback(() => {
    tokenStorage.clear();
    setMe(null);
    router.push("/login");
  }, [router]);

  const hasPermission = React.useCallback(
    (...permissions: string[]) => {
      const granted = me?.user_type === "internal" ? me.internal?.role?.permissions ?? [] : [];
      if (granted.includes("*")) return true;
      return permissions.every((permission) => granted.includes(permission));
    },
    [me]
  );

  const refreshUser = React.useCallback(async () => {
    setMe(await authApi.me());
  }, []);

  const value = React.useMemo<AuthContextValue>(
    () => ({
      user: me?.user_type === "internal" ? me.internal : null,
      customer: me?.user_type === "customer" ? me.customer : null,
      userType: me?.user_type ?? null,
      isAuthenticated: me !== null,
      isLoading,
      login,
      register,
      logout,
      hasPermission,
      refreshUser,
    }),
    [me, isLoading, login, register, logout, hasPermission, refreshUser]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = React.useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
