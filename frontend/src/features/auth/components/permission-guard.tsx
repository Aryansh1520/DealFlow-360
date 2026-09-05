"use client";

import * as React from "react";
import { ShieldX } from "lucide-react";

import { useAuth } from "@/features/auth/auth-context";

interface PermissionGuardProps {
  /** Every listed permission must be granted (a role with "*" passes everything). */
  permissions: string[];
  /** Rendered when access is denied. Defaults to a "no access" notice; pass null to render nothing. */
  fallback?: React.ReactNode;
  children: React.ReactNode;
}

const defaultFallback = (
  <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed p-12 text-center">
    <ShieldX className="h-10 w-10 text-muted-foreground" />
    <p className="text-lg font-medium">Access denied</p>
    <p className="text-sm text-muted-foreground">
      You don&apos;t have permission to view this content.
    </p>
  </div>
);

export function PermissionGuard({
  permissions,
  fallback = defaultFallback,
  children,
}: PermissionGuardProps) {
  const { hasPermission } = useAuth();

  if (!hasPermission(...permissions)) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}
