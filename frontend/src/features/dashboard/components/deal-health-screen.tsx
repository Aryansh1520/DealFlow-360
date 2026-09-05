"use client";

import * as React from "react";
import { AlertTriangle, Bell, Layers, PauseCircle, Timer } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Money } from "@/components/ui/money";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
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

  const { data: dealHealth, isLoading } = useDealHealth({ page_size: 100 });
  const { data: alerts } = useAlerts({ acknowledged: false });

  const [alertsOpen, setAlertsOpen] = React.useState(false);

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
        description="Every open deal, its margin and risk, and anything the system has flagged."
        actions={
          <div className="flex items-center gap-2">
            <LivePill connected={connected} />
            <Button
              variant={openAlerts > 0 ? "destructive" : "outline"}
              size="sm"
              onClick={() => setAlertsOpen(true)}
            >
              <Bell className="h-4 w-4" />
              Alerts
              {openAlerts > 0 && (
                <span className="ml-0.5 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-white/25 px-1 text-[10px] font-semibold leading-none text-white">
                  {openAlerts > 99 ? "99+" : openAlerts}
                </span>
              )}
            </Button>
          </div>
        }
      />

      {/* KPI strip — four equal cells, one glance. */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {isLoading ? (
          Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-[4.5rem]" />)
        ) : (
          <>
            <KpiTile icon={Layers} label="Open deals" value={openDeals} />
            <KpiTile
              icon={Timer}
              label="Value in approval"
              value={<Money minor={valueInApproval} currency={currency} compact />}
            />
            <KpiTile
              icon={PauseCircle}
              label="Stalled"
              value={stalledCount}
              tone={stalledCount > 0 ? "warning" : "neutral"}
            />
            <KpiTile
              icon={AlertTriangle}
              label="Open alerts"
              value={openAlerts}
              tone={openAlerts > 0 ? "danger" : "neutral"}
              onClick={() => setAlertsOpen(true)}
            />
          </>
        )}
      </div>

      {/* The deals table owns the full width; alerts live in the modal above. */}
      <div className="mt-6">
        <DealHealthTable />
      </div>

      <Dialog open={alertsOpen} onOpenChange={setAlertsOpen}>
        <DialogContent className="max-w-xl gap-0 overflow-hidden p-0">
          <DialogHeader className="border-b px-4 py-3 pr-10 text-left">
            <DialogTitle className="flex items-center gap-2 text-base">
              Alerts
              {openAlerts > 0 && (
                <span className="inline-flex items-center rounded-full bg-muted px-2.5 py-0.5 text-xs font-semibold tabular-nums text-muted-foreground">
                  {openAlerts}
                </span>
              )}
            </DialogTitle>
          </DialogHeader>
          <div className="max-h-[70vh] overflow-y-auto">
            <AlertsList alerts={alerts?.items ?? []} bare />
          </div>
        </DialogContent>
      </Dialog>
    </PermissionGuard>
  );
}

function LivePill({ connected }: { connected: boolean }) {
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium text-muted-foreground"
      title={connected ? "Live — updates stream in automatically" : "Reconnecting…"}
    >
      <span
        className={cn(
          "h-1.5 w-1.5 rounded-full",
          connected ? "animate-pulse bg-positive" : "bg-muted-foreground/40"
        )}
      />
      {connected ? "Live" : "Offline"}
    </span>
  );
}

const TILE_TONES = {
  neutral: "bg-muted text-muted-foreground",
  warning: "bg-warning/10 text-warning",
  danger: "bg-danger/10 text-danger",
} as const;

function KpiTile({
  icon: Icon,
  label,
  value,
  tone = "neutral",
  onClick,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: React.ReactNode;
  tone?: keyof typeof TILE_TONES;
  onClick?: () => void;
}) {
  const className = cn(
    "flex items-center gap-3 rounded-lg border bg-card p-4 text-left text-card-foreground shadow-sm",
    onClick && "w-full transition-colors hover:bg-muted/40"
  );
  const inner = (
    <>
      <span
        className={cn(
          "flex h-9 w-9 shrink-0 items-center justify-center rounded-lg",
          TILE_TONES[tone]
        )}
      >
        <Icon className="h-4 w-4" />
      </span>
      <div className="min-w-0">
        <p className="truncate text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
          {label}
        </p>
        <p className="text-xl font-semibold leading-tight tabular-nums">{value}</p>
      </div>
    </>
  );

  return onClick ? (
    <button type="button" onClick={onClick} className={className}>
      {inner}
    </button>
  ) : (
    <div className={className}>{inner}</div>
  );
}
