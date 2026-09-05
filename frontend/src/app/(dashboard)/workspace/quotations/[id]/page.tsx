"use client";

import { useParams } from "next/navigation";

import { PermissionGuard } from "@/features/auth/components/permission-guard";
import { QuotationBuilder } from "@/features/quotations/components/quotation-builder";

export default function QuotationBuilderPage() {
  const params = useParams<{ id: string }>();
  const quotationId = Number(params.id);

  return (
    <PermissionGuard permissions={["quotations:read"]}>
      <QuotationBuilder quotationId={quotationId} />
    </PermissionGuard>
  );
}
