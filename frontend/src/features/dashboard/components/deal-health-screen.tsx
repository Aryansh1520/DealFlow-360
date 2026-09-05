"use client";

import { PageHeader } from "@/components/layout/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { useInvalidateOnFrame, useLiveEvents } from "@/lib/live/use-live-events";
import { PermissionGuard } from "@/features/auth/components/permission-guard";
import { useAlerts, useDashboardSummary, useDealHealth } from "@/features/dashboard/hooks";
import { AlertsList } from "@/features/dashboard/components/alerts-list";
import { DealHealthTable } from "@/features/dashboard/components/deal-health-table";
import { StatCards } from "@/features/dashboard/components/stat-cards";

export function DealHealthScreen() {
  const invalidate = useInvalidateOnFrame();
  const { connected } = useLiveEvents("dashboard", invalidate);

  const { data: summary, isLoading: summaryLoading } = useDashboardSummary();
  const { data: alerts } = useAlerts({ acknowledged: false });
  const { data: dealHealth } = useDealHealth({ page_size: 100 });

  return (
    <PermissionGuard permissions={["dashboard:read"]}>
      <PageHeader
        title="Deal health"
        description="A denormalised read model — every row is strongly consistent with the event ledger."
      />

      {summaryLoading || !summary ? (
        <Skeleton className="h-24 w-full" />
      ) : (
        <StatCards stats={summary.data.stats} currency={summary.data.currency} />
      )}

      <div className="mt-8 grid gap-8 lg:grid-cols-[minmax(0,1fr)_380px]">
        <section>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Deals
          </h2>
          <DealHealthTable />
          {dealHealth && (
            <p className="mt-2 text-xs text-muted-foreground">
              Served from a denormalised read model · {dealHealth.elapsedMs}ms
              {connected ? " · live" : ""}
            </p>
          )}
        </section>

        <section>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Alerts
          </h2>
          <AlertsList alerts={alerts?.items ?? []} />
        </section>
      </div>
    </PermissionGuard>
  );
}
