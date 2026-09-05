"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";

import { homePathFor, useAuth } from "@/features/auth/auth-context";

export default function HomePage() {
  const { isAuthenticated, userType, isLoading } = useAuth();
  const router = useRouter();

  React.useEffect(() => {
    if (!isLoading) {
      router.replace(isAuthenticated ? homePathFor(userType) : "/login");
    }
  }, [isLoading, isAuthenticated, userType, router]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
    </div>
  );
}
