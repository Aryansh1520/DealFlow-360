"use client";

import { PageHeader } from "@/components/layout/page-header";
import { useInvalidateOnFrame, useLiveEvents } from "@/lib/live/use-live-events";
import { useAuth } from "@/features/auth/auth-context";
import { useEnums } from "@/features/meta/hooks";
import { ApprovalQueueTable } from "@/features/approvals/components/approval-queue-table";

export default function ApprovalsPage() {
  const { hasPermission } = useAuth();
  const { data: enums } = useEnums();

  // Live: a quote that re-enters approval (customer countered + confirmed, or a
  // golden-rule re-route) shows up here with no refresh.
  const invalidateOnFrame = useInvalidateOnFrame();
  useLiveEvents("approvals", invalidateOnFrame);
  // A user might hold l1, l2, both (admin) or neither — show only the levels
  // they can act on rather than a level filter dropdown.
  const levels = [
    hasPermission("approvals:l1") ? "l1_sales_manager" : null,
    hasPermission("approvals:l2") ? "l2_finance" : null,
  ].filter((level): level is string => Boolean(level));

  return (
    <div>
      <PageHeader title="Approvals" description="Quotations waiting on your review." />
      {levels.length === 0 ? (
        <p className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
          You don&apos;t hold an approval permission.
        </p>
      ) : levels.length === 1 ? (
        <ApprovalQueueTable level={levels[0]} />
      ) : (
        <div className="space-y-6">
          {levels.map((level) => (
            <div key={level} className="space-y-2">
              <h2 className="text-sm font-semibold">{enums?.labels.approval_level?.[level] ?? level}</h2>
              <ApprovalQueueTable level={level} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
