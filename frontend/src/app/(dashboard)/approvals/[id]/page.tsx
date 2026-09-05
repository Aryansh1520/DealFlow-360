"use client";

import { useParams } from "next/navigation";

import { ApprovalDetail } from "@/features/approvals/components/approval-detail";

export default function ApprovalDetailPage() {
  const params = useParams<{ id: string }>();
  return <ApprovalDetail approvalId={Number(params.id)} />;
}
