"use client";

import { PageHeader } from "@/components/layout/page-header";
import { PermissionGuard } from "@/features/auth/components/permission-guard";
import { QuotationsTable } from "@/features/quotations/components/quotations-table";

export default function QuotationsPage() {
  return (
    <div>
      <PageHeader title="Quotations" description="Every deal your team is working." />
      <PermissionGuard permissions={["quotations:read"]}>
        <QuotationsTable />
      </PermissionGuard>
    </div>
  );
}
