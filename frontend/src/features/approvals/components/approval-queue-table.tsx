"use client";

import { useRouter } from "next/navigation";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Money } from "@/components/ui/money";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { getErrorMessage } from "@/lib/api-client";
import { useEnumLabel } from "@/features/meta/hooks";
import { useApprovalQueue } from "@/features/approvals/hooks";

function waitingSince(createdAt: string): string {
  const hours = Math.floor((Date.now() - new Date(createdAt).getTime()) / 3_600_000);
  if (hours < 1) return "Just now";
  if (hours < 24) return `${hours}h`;
  return `${Math.floor(hours / 24)}d`;
}

/** `level` scopes the queue to what the logged-in user can act on
 * (`approvals:l1` → l1_sales_manager, `approvals:l2` → l2_finance) — the
 * caller passes it in from a `<PermissionGuard>`-gated context. */
export function ApprovalQueueTable({ level }: { level?: string }) {
  const { data, isLoading, isError, error } = useApprovalQueue({ level, status: "pending" });
  const router = useRouter();

  if (isError) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Failed to load approvals</AlertTitle>
        <AlertDescription>{getErrorMessage(error)}</AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="rounded-lg border bg-card shadow-sm">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Reference</TableHead>
            <TableHead>Customer</TableHead>
            <TableHead className="text-right">Total</TableHead>
            <TableHead className="text-right">Risk</TableHead>
            <TableHead>Level</TableHead>
            <TableHead>Waiting</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading ? (
            Array.from({ length: 4 }).map((_, index) => (
              <TableRow key={index}>
                {Array.from({ length: 6 }).map((__, cell) => (
                  <TableCell key={cell}>
                    <Skeleton className="h-4 w-20" />
                  </TableCell>
                ))}
              </TableRow>
            ))
          ) : data && data.length > 0 ? (
            data.map((approval) => (
              <TableRow
                key={approval.id}
                className="cursor-pointer"
                onClick={() => router.push(`/approvals/${approval.id}`)}
              >
                <TableCell className="font-medium">{approval.quotation_reference}</TableCell>
                <TableCell>{approval.customer_name}</TableCell>
                <TableCell className="text-right">
                  <Money minor={approval.total_minor} currency={approval.currency} />
                </TableCell>
                <TableCell className="text-right tabular-nums">{approval.risk_score}</TableCell>
                <TableCell>
                  <LevelBadge level={approval.level} />
                </TableCell>
                <TableCell className="text-muted-foreground">{waitingSince(approval.created_at)}</TableCell>
              </TableRow>
            ))
          ) : (
            <TableRow>
              <TableCell colSpan={6} className="h-24 text-center text-muted-foreground">
                Nothing waiting on you right now.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}

function LevelBadge({ level }: { level: string }) {
  const label = useEnumLabel("approval_level", level);
  return <Badge variant="outline">{label}</Badge>;
}
