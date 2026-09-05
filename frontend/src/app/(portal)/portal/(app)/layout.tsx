"use client";

import { LogOut } from "lucide-react";

import { APP_NAME } from "@/lib/config";
import { Button } from "@/components/ui/button";
import { AuthGuard } from "@/features/auth/components/auth-guard";
import { PortalGuard } from "@/features/auth/components/portal-guard";
import { useAuth } from "@/features/auth/auth-context";

export default function PortalAppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <PortalGuard>
        <PortalShell>{children}</PortalShell>
      </PortalGuard>
    </AuthGuard>
  );
}

function PortalShell({ children }: { children: React.ReactNode }) {
  const { customer, logout } = useAuth();

  return (
    <>
      <header className="flex items-center justify-between border-b bg-background px-4 py-3 md:px-8">
        <div>
          <p className="text-sm font-semibold">{APP_NAME} · Customer Portal</p>
          {customer && (
            <p className="text-xs text-muted-foreground">{customer.company ?? customer.name}</p>
          )}
        </div>
        <Button variant="ghost" size="sm" onClick={logout}>
          <LogOut />
          Log out
        </Button>
      </header>
      <main className="mx-auto w-full max-w-4xl p-4 md:p-8">{children}</main>
    </>
  );
}
