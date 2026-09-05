"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { ArrowDown, ArrowUp } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
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
import { useEnumLabel, useEnums, useStatusLabel } from "@/features/meta/hooks";
import { useUsers } from "@/features/users/hooks";
import { useDealHealth } from "@/features/dashboard/hooks";

type SortKey = "total_minor" | "margin_bps" | "risk_score" | "days_inactive" | "last_activity_at";

export function DealHealthTable() {
  const { data: enums } = useEnums();
  const { data: usersPage } = useUsers({ page: 1, page_size: 100 });
  const reps = (usersPage?.items ?? []).filter((u) => u.role != null);

  const [repId, setRepId] = React.useState<string>("all");
  const [stage, setStage] = React.useState<string>("all");
  const [sortBy, setSortBy] = React.useState<SortKey>("last_activity_at");
  const [sortDir, setSortDir] = React.useState<"asc" | "desc">("desc");

  const { data, isLoading } = useDealHealth({
    owner_rep_id: repId === "all" ? undefined : Number(repId),
    stage: stage === "all" ? undefined : stage,
    page_size: 100,
  });

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
    <div className="space-y-3">
      <div className="flex flex-wrap gap-3">
        <Select value={repId} onValueChange={setRepId}>
          <SelectTrigger className="w-48">
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
          <SelectTrigger className="w-48">
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
      </div>

      {isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : rows.length === 0 ? (
        <p className="rounded-md border p-6 text-sm text-muted-foreground">
          No deals match these filters.
        </p>
      ) : (
        <div className="overflow-x-auto rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Reference</TableHead>
                <TableHead>Customer</TableHead>
                <TableHead>Rep</TableHead>
                <TableHead>Stage</TableHead>
                <SortHead label="Total" active={sortBy === "total_minor"} dir={sortDir} onClick={() => toggleSort("total_minor")} align="right" />
                <SortHead label="Margin" active={sortBy === "margin_bps"} dir={sortDir} onClick={() => toggleSort("margin_bps")} align="right" />
                <SortHead label="Risk" active={sortBy === "risk_score"} dir={sortDir} onClick={() => toggleSort("risk_score")} align="right" />
                <SortHead label="Idle" active={sortBy === "days_inactive"} dir={sortDir} onClick={() => toggleSort("days_inactive")} align="right" />
                <TableHead>Flags</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((row) => (
                <DealRow key={row.quotation_id} row={row} />
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}

function SortHead({
  label,
  active,
  dir,
  onClick,
  align,
}: {
  label: string;
  active: boolean;
  dir: "asc" | "desc";
  onClick: () => void;
  align?: "right";
}) {
  return (
    <TableHead className={cn(align === "right" && "text-right")}>
      <button
        type="button"
        onClick={onClick}
        className={cn(
          "inline-flex items-center gap-1 hover:text-foreground",
          active ? "text-foreground" : "text-muted-foreground"
        )}
      >
        {label}
        {active && (dir === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
      </button>
    </TableHead>
  );
}

function DealRow({ row }: { row: DealHealthRow }) {
  const router = useRouter();
  const stageLabel = useStatusLabel(row.stage);
  return (
    <TableRow
      className="cursor-pointer"
      onClick={() => router.push(`/workspace/quotations/${row.quotation_id}`)}
    >
      <TableCell className="font-mono text-xs">{row.reference}</TableCell>
      <TableCell>{row.customer_name}</TableCell>
      <TableCell className="text-muted-foreground">{row.owner_rep_name}</TableCell>
      <TableCell>{stageLabel}</TableCell>
      <TableCell className="text-right">
        <Money minor={row.total_minor} currency={row.currency} compact />
      </TableCell>
      <TableCell className="text-right tabular-nums">{formatBps(row.margin_bps)}</TableCell>
      <TableCell className="text-right tabular-nums">{row.risk_score}</TableCell>
      <TableCell className="text-right tabular-nums">{row.days_inactive}d</TableCell>
      <TableCell>
        <div className="flex flex-wrap gap-1">
          {row.flags.map((flag) => (
            <FlagChip key={flag} flag={flag} />
          ))}
        </div>
      </TableCell>
    </TableRow>
  );
}

function FlagChip({ flag }: { flag: string }) {
  const label = useEnumLabel("alert_type", flag);
  return (
    <Badge variant="warning" className="text-[10px]">
      {label}
    </Badge>
  );
}
