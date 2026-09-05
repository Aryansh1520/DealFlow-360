"use client";

import { PageHeader } from "@/components/layout/page-header";
import { PermissionGuard } from "@/features/auth/components/permission-guard";
import { WarehousesTable } from "@/features/warehouses/components/warehouses-table";

export default function WarehousesPage() {
  return (
    <div>
      <PageHeader
        title="Warehouses"
        description="Fulfilment locations, shipping weights and stock on hand."
      />
      <PermissionGuard permissions={["warehouses:read"]}>
        <WarehousesTable />
      </PermissionGuard>
    </div>
  );
}
