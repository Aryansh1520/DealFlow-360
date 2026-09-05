"use client";

import { PageHeader } from "@/components/layout/page-header";
import { PermissionGuard } from "@/features/auth/components/permission-guard";
import { PolicyScreen } from "@/features/policies/components/policy-screen";

export default function DiscountPolicyPage() {
  return (
    <div>
      <PageHeader
        title="Discount Policy"
        description="Ceilings, weights and thresholds the decision engine evaluates every quote against."
      />
      <PermissionGuard permissions={["policies:read"]}>
        <PolicyScreen />
      </PermissionGuard>
    </div>
  );
}
