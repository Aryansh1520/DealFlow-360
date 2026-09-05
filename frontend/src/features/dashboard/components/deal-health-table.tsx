"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowDown,
  ArrowUp,
  Download,
  FileSpreadsheet,
  Loader2,
  Receipt,
  SquarePen,
  Truck,
} from "lucide-react";

import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/ui/status-badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Money } from "@/components/ui/money";
import { formatBps } from "@/lib/money";
import { cn } from "@/lib/utils";
import type { DealHealthRow } from "@/lib/api/types";
import { useAuth } from "@/features/auth/auth-context";
import { useEnumLabel, useEnums } from "@/features/meta/hooks";
import { useUsers } from "@/features/users/hooks";
import { useDealHealth, useExportDealHealth } from "@/features/dashboard/hooks";

type SortKey = "total_minor" | "margin_bps" | "risk_score" | "days_inactive" | "last_activity_at";

const COL_COUNT = 10;

const ACTIVITY_WINDOWS: { value: string; label: string; days: number | null }[] = [
  { value: "all", label: "Any time", days: null },
  { value: "7", label: "Active in 7 days", days: 7 },
  { value: "30", label: "Active in 30 days", days: 30 },
  { value: "90", label: "Active in 90 days", days: 90 },
];

type RowPerms = { builder: boolean; fulfil: boolean; bill: boolean };

export function DealHealthTable() {
  const { data: enums } = useEnums();
  const { hasPermission } = useAuth();
  const { data: usersPage } = useUsers({ page: 1, page_size: 100 });
  const reps = (usersPage?.items ?? []).filter((u) => u.role != null);

  const perms: RowPerms = {
    builder: hasPermission("quotations:read"),
    fulfil: hasPermission("fulfillment:read"),
    bill: hasPermission("billing:read"),
  };

  const [repId, setRepId] = React.useState<string>("all");
  const [stage, setStage] = React.useState<string>("all");
  const [activeWindow, setActiveWindow] = React.useState<string>("all");
  const [sortBy, setSortBy] = React.useState<SortKey>("last_activity_at");
  const [sortDir, setSortDir] = React.useState<"asc" | "desc">("desc");

  const activeSince = React.useMemo(() => {
    const win = ACTIVITY_WINDOWS.find((w) => w.value === activeWindow);
    if (!win?.days) return undefined;
    return new Date(Date.now() - win.days * 86_400_000).toISOString();
  }, [activeWindow]);

  const exportFilters = {
    owner_rep_id: repId === "all" ? undefined : Number(repId),
    stage: stage === "all" ? undefined : stage,
    active_since: activeSince,
  };

  const { data, isLoading } = useDealHealth({ ...exportFilters, page_size: 100 });
  const exportDealHealth = useExportDealHealth(exportFilters);

  const rows = React.useMemo(() => {
    const list = [...(data?.data.items ?? [])];
    list.sort((a, b) => {
      const av = a[sortBy];
      const bv = b[sortBy];
      const cmp =
        typeof av === "number" && typeof bv === "number"
          ? av - bv
          : String(av).localeCompare(String(bv));
      return sortDir === "asc" ? cmp : -cmp;
    });
    return list;
  }, [data, sortBy, sortDir]);

  const toggleSort = (key: SortKey) => {
    if (sortBy === key) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else {
      setSortBy(key);
      setSortDir("desc");
    }
  };

  return (
    <Card className="flex min-w-0 flex-col overflow-hidden">
      <div className="flex flex-col gap-3 p-4 lg:flex-row lg:items-center lg:justify-between">
        <h2 className="flex items-center gap-2 text-sm font-semibold">
          Deals
          {data && (
            <span className="inline-flex items-center rounded-full bg-muted px-2.5 py-0.5 text-xs font-semibold tabular-nums text-muted-foreground">
              {rows.length}
            </span>
          )}
        </h2>
        <div className="flex flex-wrap items-center gap-2">
          <Select value={repId} onValueChange={setRepId}>
            <SelectTrigger className="h-9 w-36">
              <SelectValue placeholder="All reps" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All reps</SelectItem>
              {reps.map((rep) => (
                <SelectItem key={rep.id} value={String(rep.id)}>
                  {rep.full_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={stage} onValueChange={setStage}>
            <SelectTrigger className="h-9 w-36">
              <SelectValue placeholder="All stages" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All stages</SelectItem>
              {(enums?.quote_status ?? []).map((s) => (
                <SelectItem key={s} value={s}>
                  {enums?.labels.quote_status?.[s] ?? s}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={activeWindow} onValueChange={setActiveWindow}>
            <SelectTrigger className="h-9 w-[10rem]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {ACTIVITY_WINDOWS.map((w) => (
                <SelectItem key={w.value} value={w.value}>
                  {w.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <span className="mx-0.5 hidden h-6 w-px bg-border sm:block" />

          <Button
            variant="outline"
            size="sm"
            disabled={exportDealHealth.isPending}
            onClick={() => exportDealHealth.mutate("pdf")}
            title="Download the full filtered set as PDF"
          >
            {exportDealHealth.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Download className="h-4 w-4" />
            )}
            PDF
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={exportDealHealth.isPending}
            onClick={() => exportDealHealth.mutate("xlsx")}
            title="Download the full filtered set as XLSX"
          >
            <FileSpreadsheet className="h-4 w-4" />
            XLSX
          </Button>
        </div>
      </div>

      <div className="max-h-[36rem] overflow-y-auto border-t">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead>Reference</TableHead>
              <TableHead>Customer</TableHead>
              <TableHead>Rep</TableHead>
              <TableHead>Stage</TableHead>
              <SortHead label="Total" active={sortBy === "total_minor"} dir={sortDir} onClick={() => toggleSort("total_minor")} />
              <SortHead label="Margin" active={sortBy === "margin_bps"} dir={sortDir} onClick={() => toggleSort("margin_bps")} />
              <SortHead label="Risk" active={sortBy === "risk_score"} dir={sortDir} onClick={() => toggleSort("risk_score")} />
              <SortHead label="Idle" active={sortBy === "days_inactive"} dir={sortDir} onClick={() => toggleSort("days_inactive")} />
              <TableHead>Flags</TableHead>
              <TableHead className="sticky right-0 w-28 border-l bg-card text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 6 }).map((_, i) => (
                <TableRow key={i} className="hover:bg-transparent">
                  {Array.from({ length: COL_COUNT }).map((__, j) => (
                    <TableCell key={j}>
                      <Skeleton className="h-4 w-full max-w-[5rem]" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : rows.length === 0 ? (
              <TableRow className="hover:bg-transparent">
                <TableCell colSpan={COL_COUNT} className="h-28 text-center text-sm text-muted-foreground">
                  No deals match these filters.
                </TableCell>
              </TableRow>
            ) : (
              rows.map((row) => <DealRow key={row.quotation_id} row={row} perms={perms} />)
            )}
          </TableBody>
        </Table>
      </div>
    </Card>
  );
}

function SortHead({
  label,
  active,
  dir,
  onClick,
}: {
  label: string;
  active: boolean;
  dir: "asc" | "desc";
  onClick: () => void;
}) {
  return (
    <TableHead className="text-right">
      <button
        type="button"
        onClick={onClick}
        className={cn(
          "ml-auto inline-flex items-center gap-1 hover:text-foreground",
          active ? "text-foreground" : "text-muted-foreground"
        )}
      >
        {label}
        {active && (dir === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
      </button>
    </TableHead>
  );
}

function DealRow({ row, perms }: { row: DealHealthRow; perms: RowPerms }) {
  const router = useRouter();
  const base = `/workspace/quotations/${row.quotation_id}`;
  return (
    <TableRow className="group cursor-pointer" onClick={() => router.push(base)}>
      <TableCell className="whitespace-nowrap font-mono text-xs font-medium text-primary group-hover:underline">
        {row.reference}
      </TableCell>
      <TableCell className="max-w-[9rem] truncate font-medium">{row.customer_name}</TableCell>
      <TableCell className="whitespace-nowrap text-muted-foreground">{row.owner_rep_name}</TableCell>
      <TableCell className="whitespace-nowrap">
        <StatusBadge status={row.stage} />
      </TableCell>
      <TableCell className="whitespace-nowrap text-right tabular-nums">
        <Money minor={row.total_minor} currency={row.currency} compact />
      </TableCell>
      <TableCell className="text-right">
        <MarginValue bps={row.margin_bps} />
      </TableCell>
      <TableCell className="text-right">
        <RiskPill score={row.risk_score} />
      </TableCell>
      <TableCell
        className={cn(
          "text-right tabular-nums",
          row.days_inactive > 7 ? "font-medium text-warning" : "text-muted-foreground"
        )}
      >
        {row.days_inactive}d
      </TableCell>
      <TableCell>
        <div className="flex flex-wrap gap-1">
          {row.flags.map((flag) => (
            <FlagChip key={flag} flag={flag} />
          ))}
        </div>
      </TableCell>
      <TableCell
        className="sticky right-0 border-l bg-card group-hover:bg-muted/50"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-end gap-0.5">
          <ActionIcon href={base} icon={SquarePen} label="Open builder" enabled={perms.builder} />
          <ActionIcon href={`${base}/fulfillment`} icon={Truck} label="Fulfilment" enabled={perms.fulfil} />
          <ActionIcon href={`${base}/billing`} icon={Receipt} label="Billing" enabled={perms.bill} />
        </div>
      </TableCell>
    </TableRow>
  );
}

function ActionIcon({
  href,
  icon: Icon,
  label,
  enabled,
}: {
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  enabled: boolean;
}) {
  if (!enabled) {
    return (
      <Button
        size="icon"
        variant="ghost"
        disabled
        className="h-7 w-7 text-muted-foreground"
        title={`${label} — no access`}
        aria-label={`${label} — no access`}
      >
        <Icon className="h-3.5 w-3.5" />
      </Button>
    );
  }
  return (
    <Button asChild size="icon" variant="ghost" className="h-7 w-7" title={label}>
      <Link href={href} onClick={(e) => e.stopPropagation()} aria-label={label}>
        <Icon className="h-3.5 w-3.5" />
      </Link>
    </Button>
  );
}

function MarginValue({ bps }: { bps: number }) {
  const tone = bps < 1500 ? "text-danger" : bps < 2000 ? "text-warning" : "text-foreground";
  return <span className={cn("tabular-nums", tone)}>{formatBps(bps)}</span>;
}

/** A soft-tinted capsule that matches `<Badge>` geometry exactly (rounded-full,
 * px-2.5, py-0.5, text-xs, font-semibold) so status / risk / flag capsules in a
 * row all read as one size. */
function RiskPill({ score }: { score: number }) {
  const tone =
    score >= 55
      ? "bg-danger/10 text-danger"
      : score >= 25
        ? "bg-warning/10 text-warning"
        : "bg-positive/10 text-positive";
  return (
    <span
      className={cn(
        "inline-flex min-w-[2.75rem] items-center justify-center rounded-full px-2.5 py-0.5 text-xs font-semibold tabular-nums",
        tone
      )}
    >
      {score}
    </span>
  );
}

const FLAG_TONE: Record<string, NonNullable<BadgeProps["variant"]>> = {
  margin_erosion: "warning",
  discount_anomaly: "danger",
  stalled_deal: "secondary",
  delivery_slippage: "info",
};

function FlagChip({ flag }: { flag: string }) {
  const label = useEnumLabel("alert_type", flag);
  return (
    <Badge variant={FLAG_TONE[flag] ?? "secondary"} className="whitespace-nowrap">
      {label}
    </Badge>
  );
}
