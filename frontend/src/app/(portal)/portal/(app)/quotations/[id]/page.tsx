"use client";

import { useParams } from "next/navigation";

import { NegotiationScreen } from "@/features/portal/components/negotiation-screen";

export default function PortalQuotationPage() {
  const params = useParams<{ id: string }>();
  return <NegotiationScreen quotationId={Number(params.id)} />;
}
