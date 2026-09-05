"use client";

import { useParams } from "next/navigation";

import { PermissionGuard } from "@/features/auth/components/permission-guard";
import { WarehouseStockPage } from "@/features/warehouses/components/warehouse-stock-page";

export default function WarehouseStockRoutePage() {
  const params = useParams<{ id: string }>();
  const warehouseId = Number(params.id);

  return (
    <PermissionGuard permissions={["warehouses:read"]}>
      <WarehouseStockPage warehouseId={warehouseId} />
    </PermissionGuard>
  );
}
