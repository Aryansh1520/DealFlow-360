"use client";

import { PageHeader } from "@/components/layout/page-header";
import { PermissionGuard } from "@/features/auth/components/permission-guard";
import { PipelineBoard } from "@/features/quotations/components/pipeline-board";

export default function PipelinePage() {
  return (
    <div>
      <PageHeader title="Pipeline" description="Every quotation, grouped by stage." />
      <PermissionGuard permissions={["quotations:read"]}>
        <PipelineBoard />
      </PermissionGuard>
    </div>
  );
}
