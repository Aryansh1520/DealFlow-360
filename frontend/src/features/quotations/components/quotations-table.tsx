"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, Plus, RefreshCw, Search } from "lucide-react";

import { getErrorMessage } from "@/lib/api-client";
import { useDebounce } from "@/lib/use-debounce";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Money } from "@/components/ui/money";
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
import { useEnums } from "@/features/meta/hooks";
import { CreateQuotationDialog } from "@/features/quotations/components/create-quotation-dialog";
import { QUOTATIONS_KEY, useQuotations } from "@/features/quotations/hooks";

const PAGE_SIZE = 10;
const ALL_STATUS = "all";

const TIER_VARIANT: Record<string, "default" | "secondary" | "outline"> = {
  gold: "default",
  silver: "secondary",
  bronze: "outline",
};

export function QuotationsTable() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { data: enums } = useEnums();

  const [page, setPage] = React.useState(1);
  const [searchInput, setSearchInput] = React.useState("");
  const search = useDebounce(searchInput);
  const [statusFilter, setStatusFilter] = React.useState(ALL_STATUS);
  const [createOpen, setCreateOpen] = React.useState(false);
  const [reloading, setReloading] = React.useState(false);

  const { data, isLoading, isError, error } = useQuotations({
    page,
    page_size: PAGE_SIZE,
    q: search || undefined,
    status: statusFilter === ALL_STATUS ? undefined : statusFilter,
  });

  React.useEffect(() => setPage(1), [search, statusFilter]);

  const handleReload = async () => {
    setReloading(true);
    await queryClient.invalidateQueries({ queryKey: [QUOTATIONS_KEY] });
    setReloading(false);
  };

  if (isError) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Failed to load quotations</AlertTitle>
        <AlertDescription>{getErrorMessage(error)}</AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative w-full max-w-sm">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search reference or customer..."
              className="pl-9"
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
            />
          </div>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-44">
              <SelectValue placeholder="All statuses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL_STATUS}>All statuses</SelectItem>
              {enums?.quote_status.map((status) => (
                <SelectItem key={status} value={status}>
                  {enums.labels.quote_status?.[status] ?? status}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button variant="outline" onClick={handleReload} disabled={reloading}>
            <RefreshCw className={reloading ? "animate-spin" : ""} />
            Reload Data
          </Button>
        </div>
        <Button onClick={() => setCreateOpen(true)}>
          <Plus />
          New quotation
        </Button>
      </div>

      <div className="rounded-lg border bg-card shadow-sm">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Reference</TableHead>
              <TableHead>Customer</TableHead>
              <TableHead>Owner</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Total</TableHead>
              <TableHead className="text-right">Risk</TableHead>
              <TableHead>Last activity</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 6 }).map((_, index) => (
                <TableRow key={index}>
                  {Array.from({ length: 7 }).map((__, cell) => (
                    <TableCell key={cell}>
                      <Skeleton className="h-4 w-20" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : data && data.items.length > 0 ? (
              data.items.map((quotation) => (
                <TableRow
                  key={quotation.id}
                  className="cursor-pointer"
                  onClick={() => router.push(`/workspace/quotations/${quotation.id}`)}
                >
                  <TableCell className="font-medium">{quotation.reference}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1.5">
                      {quotation.customer_name}
                      <Badge variant={TIER_VARIANT[quotation.customer_tier]} className="capitalize">
                        {quotation.customer_tier}
                      </Badge>
                    </div>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{quotation.owner_rep_name}</TableCell>
                  <TableCell>
                    <StatusBadge status={quotation.status} />
                  </TableCell>
                  <TableCell className="text-right">
                    <Money minor={quotation.computation.total_minor} currency={quotation.currency} />
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {quotation.computation.risk_score}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {new Date(quotation.last_activity_at).toLocaleDateString()}
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={7} className="h-24 text-center text-muted-foreground">
                  No quotations found.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {data && data.pages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Page {data.page} of {data.pages} · {data.total} quotations
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((current) => current - 1)}
            >
              <ChevronLeft />
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= data.pages}
              onClick={() => setPage((current) => current + 1)}
            >
              Next
              <ChevronRight />
            </Button>
          </div>
        </div>
      )}

      <CreateQuotationDialog open={createOpen} onOpenChange={setCreateOpen} />
    </div>
  );
}
