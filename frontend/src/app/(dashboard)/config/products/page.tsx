"use client";

import { PageHeader } from "@/components/layout/page-header";
import { PermissionGuard } from "@/features/auth/components/permission-guard";
import { ProductsTable } from "@/features/catalog/components/products-table";

export default function ProductsPage() {
  return (
    <div>
      <PageHeader title="Products" description="The catalogue sold on every quotation." />
      <PermissionGuard permissions={["catalog:read"]}>
        <ProductsTable />
      </PermissionGuard>
    </div>
  );
}
