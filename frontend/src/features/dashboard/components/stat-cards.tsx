"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Money } from "@/components/ui/money";
import { formatBps } from "@/lib/money";
import type { DashboardStat } from "@/lib/api/types";

function renderValue(stat: DashboardStat, currency: string) {
  switch (stat.unit) {
    case "currency":
      return <Money minor={stat.value} currency={currency} compact />;
    case "bps":
      return formatBps(stat.value);
    case "days":
      return `${stat.value}d`;
    default:
      return stat.value.toLocaleString();
  }
}

export function StatCards({
  stats,
  currency,
}: {
  stats: DashboardStat[];
  currency: string;
}) {
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {stats.map((stat) => (
        <Card key={stat.key}>
          <CardContent className="p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              {stat.label}
            </p>
            <p className="mt-1 text-2xl font-semibold tabular-nums">
              {renderValue(stat, currency)}
            </p>
            {stat.hint && <p className="mt-0.5 text-xs text-muted-foreground">{stat.hint}</p>}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
