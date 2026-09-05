"use client";

import * as React from "react";
import { Download, FileSpreadsheet, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Money } from "@/components/ui/money";
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
import { formatBps, formatMoney } from "@/lib/money";
import { PageHeader } from "@/components/layout/page-header";
import { PermissionGuard } from "@/features/auth/components/permission-guard";
import { useAuth } from "@/features/auth/auth-context";
import { useCategories } from "@/features/catalog/hooks";
import { useEnums } from "@/features/meta/hooks";
import { useUsers } from "@/features/users/hooks";
import type { SalesReportFilters } from "@/features/reports/api";
import { useExportReport, useSalesReport } from "@/features/reports/hooks";

const PAGE_SIZE = 20;
const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];
const CURRENT = new Date();
const YEARS = Array.from({ length: 6 }, (_, i) => CURRENT.getFullYear() - i);

const thisMonth = () =>
  `${CURRENT.getFullYear()}-${String(CURRENT.getMonth() + 1).padStart(2, "0")}`;

export function ReportsScreen() {
  const { hasPermission } = useAuth();
  const { data: enums } = useEnums();
  const { data: usersPage } = useUsers({ page: 1, page_size: 100 });
  const { data: categoriesPage } = useCategories();

  const [period, setPeriod] = React.useState(thisMonth());
  const [repId, setRepId] = React.useState("all");
  const [status, setStatus] = React.useState("all");
  const [categoryId, setCategoryId] = React.useState("all");
  const [page, setPage] = React.useState(1);

  // Any filter change resets to the first page.
  React.useEffect(() => setPage(1), [period, repId, status, categoryId]);

  const filters: SalesReportFilters = {
    period: period || undefined,
    rep_id: repId === "all" ? undefined : Number(repId),
    approval_status: status === "all" ? undefined : status,
    category_id: categoryId === "all" ? undefined : Number(categoryId),
  };

  const { data, isLoading } = useSalesReport(filters);
  const exportReport = useExportReport(filters);
  const rows = data?.items ?? [];

  const totalValue = rows.reduce((sum, r) => sum + r.total_minor, 0);
  const currency = rows[0]?.currency ?? "INR";
  const capped = (data?.total ?? 0) > rows.length;

  const pageCount = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  const safePage = Math.min(page, pageCount);
  const pageRows = rows.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  // Revenue-by-rep, across the whole filtered set (not just the visible page).
  const byRep = React.useMemo(() => {
    const map = new Map<string, number>();
    for (const r of rows) map.set(r.owner_rep_name, (map.get(r.owner_rep_name) ?? 0) + r.total_minor);
    return [...map.entries()].sort((a, b) => b[1] - a[1]);
  }, [rows]);
  const maxRep = Math.max(1, ...byRep.map(([, v]) => v));

  return (
    <PermissionGuard permissions={["reports:read"]}>
      <PageHeader title="Sales report" description="Filter, review and export." />

      <Card className="mb-6">
        <CardContent className="grid gap-4 p-4 sm:grid-cols-2 lg:grid-cols-4">
          <Field label="Period">
            <PeriodSelect value={period} onChange={setPeriod} />
          </Field>
          <Field label="Rep">
            <Select value={repId} onValueChange={setRepId}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All reps</SelectItem>
                {(usersPage?.items ?? [])
                  .filter((u) => u.role != null)
                  .map((u) => (
                    <SelectItem key={u.id} value={String(u.id)}>
                      {u.full_name}
                    </SelectItem>
                  ))}
              </SelectContent>
            </Select>
          </Field>
          <Field label="Approval status">
            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Any status</SelectItem>
                {(enums?.quote_status ?? []).map((s) => (
                  <SelectItem key={s} value={s}>
                    {enums?.labels.quote_status?.[s] ?? s}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>
          <Field label="Category">
            <Select value={categoryId} onValueChange={setCategoryId}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All categories</SelectItem>
                {(categoriesPage?.items ?? []).map((c) => (
                  <SelectItem key={c.id} value={String(c.id)}>
                    {c.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>
        </CardContent>
      </Card>

      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground">
          {rows.length} row{rows.length === 1 ? "" : "s"} · total{" "}
          <Money minor={totalValue} currency={currency} className="font-medium text-foreground" />
        </p>
        {hasPermission("reports:export") && (
          <div className="flex items-center gap-2">
            <span className="hidden text-xs text-muted-foreground sm:inline">
              Exports the full filtered set
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={exportReport.isPending}
              onClick={() => exportReport.mutate("pdf")}
            >
              {exportReport.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Download className="h-4 w-4" />
              )}
              PDF
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={exportReport.isPending}
              onClick={() => exportReport.mutate("xlsx")}
            >
              <FileSpreadsheet className="h-4 w-4" />
              XLSX
            </Button>
          </div>
        )}
      </div>

      {byRep.length > 1 && (
        <Card className="mb-6">
          <CardContent className="space-y-2 p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Revenue by rep
            </p>
            {byRep.map(([name, value]) => (
              <div key={name} className="flex items-center gap-3 text-sm">
                <span className="w-32 shrink-0 truncate text-muted-foreground">{name}</span>
                <div className="h-3 flex-1 rounded bg-muted">
                  <div
                    className="h-3 rounded bg-primary"
                    style={{ width: `${(value / maxRep) * 100}%` }}
                  />
                </div>
                <span className="w-24 shrink-0 text-right tabular-nums">
                  {formatMoney(value, currency, { compact: true })}
                </span>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : rows.length === 0 ? (
        <p className="rounded-md border p-6 text-sm text-muted-foreground">
          Nothing matches these filters.
        </p>
      ) : (
        <>
          {capped && (
            <p className="mb-3 text-xs text-muted-foreground">
              Showing the first {rows.length} of {data?.total} rows — narrow the filters, or
              export for the complete set.
            </p>
          )}
          <div className="overflow-x-auto rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Period</TableHead>
                  <TableHead>Reference</TableHead>
                  <TableHead>Customer</TableHead>
                  <TableHead>Rep</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Total</TableHead>
                  <TableHead className="text-right">Margin</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {pageRows.map((row) => (
                  <TableRow key={row.quotation_id}>
                    <TableCell className="whitespace-nowrap tabular-nums">{row.period}</TableCell>
                    <TableCell className="font-mono text-xs">{row.reference}</TableCell>
                    <TableCell>{row.customer_name}</TableCell>
                    <TableCell className="text-muted-foreground">{row.owner_rep_name}</TableCell>
                    <TableCell className="capitalize">{row.status}</TableCell>
                    <TableCell className="text-right">
                      <Money minor={row.total_minor} currency={row.currency} />
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatBps(row.margin_bps)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {rows.length > PAGE_SIZE && (
            <div className="mt-3 flex items-center justify-between text-sm">
              <span className="text-muted-foreground">
                Page {safePage} of {pageCount}
                <span className="hidden sm:inline"> · rows {(safePage - 1) * PAGE_SIZE + 1}–
                  {Math.min(safePage * PAGE_SIZE, rows.length)} of {rows.length}
                </span>
              </span>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={safePage <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={safePage >= pageCount}
                  onClick={() => setPage((p) => Math.min(pageCount, p + 1))}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </PermissionGuard>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs text-muted-foreground">{label}</Label>
      {children}
    </div>
  );
}

/** Year + month, emitting "YYYY-MM" (or "" for all-time). */
function PeriodSelect({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const [yearStr, monthStr] = value ? value.split("-") : ["", ""];
  const year = value ? yearStr : "all";
  const month = value ? String(Number(monthStr)) : String(CURRENT.getMonth() + 1);

  const setYear = (next: string) => {
    if (next === "all") return onChange("");
    const mm = value ? Number(monthStr) : CURRENT.getMonth() + 1;
    onChange(`${next}-${String(mm).padStart(2, "0")}`);
  };
  const setMonth = (next: string) => {
    const yy = value ? yearStr : String(CURRENT.getFullYear());
    onChange(`${yy}-${String(Number(next)).padStart(2, "0")}`);
  };

  return (
    <div className="flex gap-2">
      <Select value={year} onValueChange={setYear}>
        <SelectTrigger className="w-28 shrink-0">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All time</SelectItem>
          {YEARS.map((y) => (
            <SelectItem key={y} value={String(y)}>
              {y}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {value && (
        <Select value={month} onValueChange={setMonth}>
          <SelectTrigger className="min-w-0 flex-1">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {MONTHS.map((name, i) => (
              <SelectItem key={name} value={String(i + 1)}>
                {name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}
    </div>
  );
}
