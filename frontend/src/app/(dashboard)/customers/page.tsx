"use client";

import { PageHeader } from "@/components/layout/page-header";
import { PermissionGuard } from "@/features/auth/components/permission-guard";
import { CustomersTable } from "@/features/customers/components/customers-table";

export default function CustomersPage() {
  return (
    <div>
      <PageHeader title="Customers" description="Manage customer accounts and portal access." />

      <PermissionGuard permissions={["customers:read"]}>
        <CustomersTable />
      </PermissionGuard>
    </div>
  );
}
