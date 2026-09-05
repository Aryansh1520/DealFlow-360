"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";

import { homePathFor, useAuth } from "@/features/auth/auth-context";

/** Renders children only for customer (portal) sessions; bounces a signed-in staff
 * member to the dashboard. Expects to be nested inside `AuthGuard`. */
export function PortalGuard({ children }: { children: React.ReactNode }) {
  const { userType, isLoading } = useAuth();
  const router = useRouter();
  const wrongType = userType !== null && userType !== "customer";

  React.useEffect(() => {
    if (!isLoading && wrongType) {
      router.replace(homePathFor(userType));
    }
  }, [isLoading, wrongType, userType, router]);

  if (isLoading || wrongType) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return <>{children}</>;
}
