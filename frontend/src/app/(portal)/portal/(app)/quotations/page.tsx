"use client";

import { PortalQuotationList } from "@/features/portal/components/portal-quotation-list";

export default function PortalQuotationsPage() {
  return (
    <div>
      <h1 className="mb-1 text-2xl font-semibold tracking-tight">Your quotations</h1>
      <p className="mb-6 text-sm text-muted-foreground">
        Review what your rep has sent, ask questions, and confirm when you&apos;re ready.
      </p>
      <PortalQuotationList />
    </div>
  );
}
