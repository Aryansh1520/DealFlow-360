"use client";

import Link from "next/link";
import { ArrowRight, Gauge } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/layout/page-header";
import { useAuth } from "@/features/auth/auth-context";
import { useDashboardSummary } from "@/features/dashboard/hooks";
import { AlertsList } from "@/features/dashboard/components/alerts-list";
import { StatCards } from "@/features/dashboard/components/stat-cards";

const DASHBOARD_COPY: Record<string, { title: string; blurb: string }> = {
  super_admin: {
    title: "Organisation overview",
    blurb: "Pipeline, revenue, approvals and alerts across the whole team.",
  },
  sales_manager: {
    title: "Sales manager dashboard",
    blurb: "Your approval queue, open pipeline and anything that's stalled.",
  },
  finance_ops: {
    title: "Finance & operations dashboard",
    blurb: "Receivables, confirmed value and sign-offs waiting on you.",
  },
  generic: {
    title: "Dashboard",
    blurb: "Your deals at a glance.",
  },
};

export function RoleDashboard() {
  const { user, hasPermission } = useAuth();
  const { data, isLoading } = useDashboardSummary();

  const dashboardType = data?.data.dashboard_type ?? user?.role?.dashboard_type ?? "generic";
  const copy = DASHBOARD_COPY[dashboardType] ?? DASHBOARD_COPY.generic;

  return (
    <div>
      <PageHeader
        title={copy.title}
        description={`${copy.blurb}${user ? `  ·  ${user.full_name}` : ""}`}
        actions={
          hasPermission("dashboard:read") ? (
            <Button asChild variant="outline" size="sm">
              <Link href="/dashboard/deal-health">
                <Gauge className="h-4 w-4" /> Deal health
              </Link>
            </Button>
          ) : undefined
        }
      />

      {isLoading || !data ? (
        <Skeleton className="h-24 w-full" />
      ) : (
        <>
          <StatCards stats={data.data.stats} currency={data.data.currency} />

          {data.data.alerts.length > 0 && (
            <div className="mt-8">
              <AlertsList
                alerts={data.data.alerts}
                compact
                action={
                  <Link
                    href="/dashboard/deal-health"
                    className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                  >
                    All alerts <ArrowRight className="h-3 w-3" />
                  </Link>
                }
              />
            </div>
          )}
        </>
      )}

      <Card className="mt-8 max-w-md">
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Your account</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <Row label="Name" value={user?.full_name} />
          <Row label="Email" value={user?.email} />
          <Row label="Role" value={user?.role?.name ?? "—"} />
          <Row label="Dashboard" value={dashboardType} />
        </CardContent>
      </Card>
    </div>
  );
}

function Row({ label, value }: { label: string; value?: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value ?? "—"}</span>
    </div>
  );
}
