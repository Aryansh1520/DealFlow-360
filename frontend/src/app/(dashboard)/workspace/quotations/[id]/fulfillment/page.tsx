"use client";

import { useParams } from "next/navigation";

import { FulfillmentScreen } from "@/features/fulfillment/components/fulfillment-screen";

export default function FulfillmentPage() {
  const params = useParams<{ id: string }>();
  return <FulfillmentScreen quotationId={Number(params.id)} />;
}
