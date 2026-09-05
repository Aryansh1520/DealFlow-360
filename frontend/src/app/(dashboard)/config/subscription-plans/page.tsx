"use client";

import { PageHeader } from "@/components/layout/page-header";
import { PermissionGuard } from "@/features/auth/components/permission-guard";
import { PlansTable } from "@/features/subscriptions/components/plans-table";

export default function SubscriptionPlansPage() {
  return (
    <div>
      <PageHeader
        title="Subscription Plans"
        description="Recurring billing terms available on subscription line items."
      />
      <PermissionGuard permissions={["subscriptions:read"]}>
        <PlansTable />
      </PermissionGuard>
    </div>
  );
}
