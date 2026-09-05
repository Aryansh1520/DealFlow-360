"use client";

import Link from "next/link";
import { BellRing, Check, ExternalLink } from "lucide-react";

import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { useEnumLabel } from "@/features/meta/hooks";
import type { AlertRead } from "@/lib/api/types";
import { useAcknowledgeAlert, useNudgeAlert } from "@/features/dashboard/hooks";

const SEVERITY_TONE: Record<string, NonNullable<BadgeProps["variant"]>> = {
  high: "danger",
  medium: "warning",
  low: "secondary",
};

export function AlertsList({ alerts, compact }: { alerts: AlertRead[]; compact?: boolean }) {
  const nudge = useNudgeAlert();
  const acknowledge = useAcknowledgeAlert();

  if (alerts.length === 0) {
    return (
      <Card>
        <CardContent className="p-6 text-sm text-muted-foreground">
          No open alerts. All deals are behaving.
        </CardContent>
      </Card>
    );
  }

  // Group by alert_type.
  const groups = new Map<string, AlertRead[]>();
  for (const alert of alerts) {
    if (!groups.has(alert.alert_type)) groups.set(alert.alert_type, []);
    groups.get(alert.alert_type)!.push(alert);
  }

  return (
    <div className="space-y-4">
      {[...groups.entries()].map(([type, groupAlerts]) => (
        <AlertGroup
          key={type}
          type={type}
          alerts={groupAlerts}
          compact={compact}
          onNudge={(id) => nudge.mutate(id)}
          onAcknowledge={(id) => acknowledge.mutate(id)}
        />
      ))}
    </div>
  );
}

function AlertGroup({
  type,
  alerts,
  compact,
  onNudge,
  onAcknowledge,
}: {
  type: string;
  alerts: AlertRead[];
  compact?: boolean;
  onNudge: (id: number) => void;
  onAcknowledge: (id: number) => void;
}) {
  const label = useEnumLabel("alert_type", type);
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-sm">
          {label}
          <Badge variant="secondary">{alerts.length}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {alerts.map((alert) => (
          <div
            key={alert.id}
            className={cn(
              "rounded-md border p-3",
              alert.acknowledged && "opacity-60"
            )}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <Badge variant={SEVERITY_TONE[alert.severity] ?? "secondary"}>
                    {alert.severity}
                  </Badge>
                  <span className="text-sm font-medium">{alert.title}</span>
                </div>
                {/* `detail` rendered verbatim — it is the explanation, not decoration. */}
                <p className="mt-1 text-sm text-muted-foreground">{alert.detail}</p>
                <Link
                  href={`/workspace/quotations/${alert.quotation_id}`}
                  className="mt-1 inline-flex items-center gap-1 text-xs text-primary hover:underline"
                >
                  {alert.quotation_reference} <ExternalLink className="h-3 w-3" />
                </Link>
              </div>
              {!compact && !alert.acknowledged && (
                <div className="flex shrink-0 gap-1">
                  <Button
                    size="sm"
                    variant="ghost"
                    title="Nudge the owning rep"
                    onClick={() => onNudge(alert.id)}
                  >
                    <BellRing className="h-4 w-4" />
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    title="Acknowledge"
                    onClick={() => onAcknowledge(alert.id)}
                  >
                    <Check className="h-4 w-4" />
                  </Button>
                </div>
              )}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
