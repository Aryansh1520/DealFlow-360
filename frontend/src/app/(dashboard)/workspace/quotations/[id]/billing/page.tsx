"use client";

import { useParams } from "next/navigation";

import { BillingScreen } from "@/features/billing/components/billing-screen";

export default function BillingPage() {
  const params = useParams<{ id: string }>();
  return <BillingScreen quotationId={Number(params.id)} />;
}
