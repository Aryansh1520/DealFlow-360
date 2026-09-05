"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";

import { homePathFor, useAuth } from "@/features/auth/auth-context";

/** Renders children only for internal (staff) sessions; bounces a signed-in customer
 * to the portal. Expects to be nested inside `AuthGuard`, which handles the
 * not-signed-in-at-all case. */
export function InternalGuard({ children }: { children: React.ReactNode }) {
  const { userType, isLoading } = useAuth();
  const router = useRouter();
  const wrongType = userType !== null && userType !== "internal";

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
