"use client";

import { PageHeader } from "@/components/layout/page-header";
import { PermissionGuard } from "@/features/auth/components/permission-guard";
import { RolesTable } from "@/features/roles/components/roles-table";

export default function RolesPage() {
  return (
    <div>
      <PageHeader title="Roles" description="Manage roles and their permissions." />

      <PermissionGuard permissions={["roles:read"]}>
        <RolesTable />
      </PermissionGuard>
    </div>
  );
}
