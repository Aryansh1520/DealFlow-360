"use client";

import { PageHeader } from "@/components/layout/page-header";
import { useAuth } from "@/features/auth/auth-context";
import { PermissionGuard } from "@/features/auth/components/permission-guard";
import { ApprovalQueueTable } from "@/features/approvals/components/approval-queue-table";

export default function ApprovalsPage() {
  const { hasPermission } = useAuth();
  // A user might hold l1, l2, both (admin) or neither — show only the levels
  // they can act on rather than a level filter dropdown.
  const levels = [
    hasPermission("approvals:l1") ? "l1_sales_manager" : null,
    hasPermission("approvals:l2") ? "l2_finance" : null,
  ].filter((level): level is string => Boolean(level));

  return (
    <div>
      <PageHeader title="Approvals" description="Quotations waiting on your review." />
      <PermissionGuard permissions={[]} fallback={null}>
        <div className="space-y-6">
          {levels.length === 0 ? (
            <p className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
              You don&apos;t hold an approval permission.
            </p>
          ) : levels.length === 1 ? (
            <ApprovalQueueTable level={levels[0]} />
          ) : (
            levels.map((level) => (
              <div key={level} className="space-y-2">
                <h2 className="text-sm font-semibold capitalize">
                  {level === "l1_sales_manager" ? "Sales Manager" : "Finance"}
                </h2>
                <ApprovalQueueTable level={level} />
              </div>
            ))
          )}
        </div>
      </PermissionGuard>
    </div>
  );
}
