"use client";

import { PageHeader } from "@/components/layout/page-header";
import { PermissionGuard } from "@/features/auth/components/permission-guard";
import { PriceListsPanel } from "@/features/pricing/components/price-lists-panel";

export default function PriceListsPage() {
  return (
    <div>
      <PageHeader
        title="Price Lists"
        description="Per-tier price overrides resolved by the pricing engine."
      />
      <PermissionGuard permissions={["pricing:read"]}>
        <PriceListsPanel />
      </PermissionGuard>
    </div>
  );
}
