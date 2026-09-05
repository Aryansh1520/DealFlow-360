"use client";

import { PageHeader } from "@/components/layout/page-header";
import { PermissionGuard } from "@/features/auth/components/permission-guard";
import { UsersTable } from "@/features/users/components/users-table";

export default function UsersPage() {
  return (
    <div>
      <PageHeader title="Users" description="Manage user accounts and their roles." />

      <PermissionGuard permissions={["users:read"]}>
        <UsersTable />
      </PermissionGuard>
    </div>
  );
}
