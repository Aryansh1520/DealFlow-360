"use client";

import * as React from "react";
import Link from "next/link";
import { BellRing, Check, ExternalLink } from "lucide-react";

import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { useEnumLabel } from "@/features/meta/hooks";
import type { AlertRead } from "@/lib/api/types";
import { useAcknowledgeAlert, useNudgeAlert } from "@/features/dashboard/hooks";

const SEVERITY_BORDER: Record<string, string> = {
  high: "border-l-danger",
  medium: "border-l-warning",
  low: "border-l-transparent",
};

const SEVERITY_TONE: Record<string, NonNullable<BadgeProps["variant"]>> = {
  high: "danger",
  medium: "warning",
  low: "secondary",
};

export function AlertsList({
  alerts,
  compact,
  action,
  bare,
}: {
  alerts: AlertRead[];
  /** Hide the per-alert nudge / acknowledge buttons (used on the summary dashboard). */
  compact?: boolean;
  /** Optional trailing control in the header, e.g. an "All alerts →" link. */
  action?: React.ReactNode;
  /** Render just the grouped list — no surrounding Card or header. For embedding
   * inside a dialog / sheet that supplies its own chrome. */
  bare?: boolean;
}) {
  const nudge = useNudgeAlert();
  const acknowledge = useAcknowledgeAlert();

  // Group by alert_type, preserving first-seen order.
  const groups = new Map<string, AlertRead[]>();
  for (const alert of alerts) {
    const bucket = groups.get(alert.alert_type);
    if (bucket) bucket.push(alert);
    else groups.set(alert.alert_type, [alert]);
  }

  const body =
    alerts.length === 0 ? (
      <p className={cn("px-4 py-10 text-center text-sm text-muted-foreground", !bare && "border-t")}>
        Nothing flagged — every deal is behaving.
      </p>
    ) : (
      <div className={cn("divide-y", !bare && "border-t")}>
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

  if (bare) return body;

  return (
    <Card className="flex flex-col overflow-hidden">
      <div className="flex items-center justify-between gap-2 p-4">
        <h2 className="flex items-center gap-2 text-sm font-semibold">
          Alerts
          {alerts.length > 0 && (
            <span className="inline-flex items-center rounded-full bg-muted px-2.5 py-0.5 text-xs font-semibold tabular-nums text-muted-foreground">
              {alerts.length}
            </span>
          )}
        </h2>
        {action}
      </div>
      {body}
    </Card>
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
    <div className="py-1.5">
      <div className="flex items-center gap-2 px-4 py-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        <span>{label}</span>
        <span className="font-normal tabular-nums">{alerts.length}</span>
      </div>
      <ul>
        {alerts.map((alert) => (
          <li key={alert.id}>
            <AlertItem
              alert={alert}
              compact={compact}
              onNudge={onNudge}
              onAcknowledge={onAcknowledge}
            />
          </li>
        ))}
      </ul>
    </div>
  );
}

function AlertItem({
  alert,
  compact,
  onNudge,
  onAcknowledge,
}: {
  alert: AlertRead;
  compact?: boolean;
  onNudge: (id: number) => void;
  onAcknowledge: (id: number) => void;
}) {
  return (
    <div
      className={cn(
        "group flex gap-3 border-l-2 py-2.5 pl-3.5 pr-3 transition-colors hover:bg-muted/40",
        SEVERITY_BORDER[alert.severity] ?? "border-l-transparent",
        alert.acknowledged && "opacity-55"
      )}
    >
      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex items-start gap-2">
          <Badge variant={SEVERITY_TONE[alert.severity] ?? "secondary"} className="mt-0.5 shrink-0 capitalize">
            {alert.severity}
          </Badge>
          <p className="text-sm font-medium leading-snug">{alert.title}</p>
        </div>
        {/* `detail` is the explanation, rendered verbatim — not decoration. */}
        <p className="text-xs leading-relaxed text-muted-foreground">{alert.detail}</p>
        <Link
          href={`/workspace/quotations/${alert.quotation_id}`}
          className="inline-flex items-center gap-1 font-mono text-[11px] text-primary hover:underline"
        >
          {alert.quotation_reference}
          <ExternalLink className="h-3 w-3" />
        </Link>
      </div>
      {!compact && !alert.acknowledged && (
        <div className="flex shrink-0 items-start gap-0.5 text-muted-foreground opacity-60 transition-opacity focus-within:opacity-100 group-hover:opacity-100">
          <Button
            size="icon"
            variant="ghost"
            className="h-7 w-7"
            title="Nudge the owning rep"
            onClick={() => onNudge(alert.id)}
          >
            <BellRing className="h-3.5 w-3.5" />
          </Button>
          <Button
            size="icon"
            variant="ghost"
            className="h-7 w-7"
            title="Acknowledge"
            onClick={() => onAcknowledge(alert.id)}
          >
            <Check className="h-3.5 w-3.5" />
          </Button>
        </div>
      )}
    </div>
  );
}
