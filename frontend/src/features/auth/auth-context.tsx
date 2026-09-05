"use client";

import * as React from "react";
import { useRouter } from "next/navigation";

import { tokenStorage } from "@/lib/api-client";
import { authApi } from "@/features/auth/api";
import type { LoginPayload, RegisterPayload, User } from "@/features/auth/types";

interface AuthContextValue {
  user: User | null;
  /** True while the initial session restore is in flight. */
  isLoading: boolean;
  login: (payload: LoginPayload) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => void;
  /** True when the user's role grants every listed permission ("*" grants all). */
  hasPermission: (...permissions: string[]) => boolean;
  refreshUser: () => Promise<void>;
}

const AuthContext = React.createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = React.useState<User | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);

  React.useEffect(() => {
    if (!tokenStorage.getAccess()) {
      setIsLoading(false);
      return;
    }
    authApi
      .me()
      .then(setUser)
      .catch(() => tokenStorage.clear())
      .finally(() => setIsLoading(false));
  }, []);

  const login = React.useCallback(async (payload: LoginPayload) => {
    const tokens = await authApi.login(payload);
    tokenStorage.set(tokens);
    setUser(await authApi.me());
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
    setUser(null);
    router.push("/login");
  }, [router]);

  const hasPermission = React.useCallback(
    (...permissions: string[]) => {
      const granted = user?.role?.permissions ?? [];
      if (granted.includes("*")) return true;
      return permissions.every((permission) => granted.includes(permission));
    },
    [user]
  );

  const refreshUser = React.useCallback(async () => {
    setUser(await authApi.me());
  }, []);

  const value = React.useMemo(
    () => ({ user, isLoading, login, register, logout, hasPermission, refreshUser }),
    [user, isLoading, login, register, logout, hasPermission, refreshUser]
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
