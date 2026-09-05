"use client";

import * as React from "react";

import { Card, CardContent } from "@/components/ui/card";
import { Money } from "@/components/ui/money";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/layout/page-header";
import { useInvalidateOnFrame, useLiveEvents } from "@/lib/live/use-live-events";
import { PermissionGuard } from "@/features/auth/components/permission-guard";
import { useAlerts, useDealHealth } from "@/features/dashboard/hooks";
import { AlertsList } from "@/features/dashboard/components/alerts-list";
import { DealHealthTable } from "@/features/dashboard/components/deal-health-table";

const TERMINAL = new Set(["paid", "rejected", "cancelled", "expired"]);
const IN_APPROVAL = new Set(["pending_l1", "pending_l2"]);

export function DealHealthScreen() {
  const invalidate = useInvalidateOnFrame();
  const { connected } = useLiveEvents("dashboard", invalidate);

  const { data: dealHealth, isLoading } = useDealHealth({ page_size: 200 });
  const { data: alerts } = useAlerts({ acknowledged: false });

  const rows = dealHealth?.data.items ?? [];
  const currency = rows[0]?.currency ?? "INR";

  const openDeals = rows.filter((r) => !TERMINAL.has(r.stage)).length;
  const valueInApproval = rows
    .filter((r) => IN_APPROVAL.has(r.stage))
    .reduce((sum, r) => sum + r.total_minor, 0);
  const stalledCount = rows.filter((r) => r.flags.includes("stalled_deal")).length;
  const openAlerts = alerts?.total ?? 0;

  return (
    <PermissionGuard permissions={["dashboard:read"]}>
      <PageHeader
        title="Deal health"
        description="A denormalised read model — every row is strongly consistent with the event ledger."
      />

      {isLoading ? (
        <Skeleton className="h-24 w-full" />
      ) : (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <Tile label="Open deals" value={openDeals} />
          <Tile
            label="Value in approval"
            value={<Money minor={valueInApproval} currency={currency} compact />}
          />
          <Tile label="Stalled" value={stalledCount} />
          <Tile label="Open alerts" value={openAlerts} />
        </div>
      )}

      <div className="mt-8 grid gap-8 lg:grid-cols-[minmax(0,1fr)_360px]">
        <section className="min-w-0">
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

        <section className="min-w-0">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Alerts
          </h2>
          <AlertsList alerts={alerts?.items ?? []} />
        </section>
      </div>
    </PermissionGuard>
  );
}

function Tile({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
        <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
      </CardContent>
    </Card>
  );
}
