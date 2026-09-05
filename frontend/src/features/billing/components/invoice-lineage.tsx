"use client";

import { ArrowRight } from "lucide-react";

import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { useInvoiceLineage } from "@/features/billing/hooks";

/** The supersession chain as a small stepper: INV-…-045 → CN-…-012 → INV-…-046.
 * Makes the immutability story visible instead of asserted. */
export function InvoiceLineage({ invoiceId }: { invoiceId: number }) {
  const { data: chain, isLoading } = useInvoiceLineage(invoiceId);

  if (isLoading) return <Skeleton className="h-10 w-full" />;
  if (!chain || chain.length <= 1) return null;

  return (
    <div className="rounded-md border bg-muted/30 p-3">
      <p className="mb-2 text-xs font-medium text-muted-foreground">Supersession chain</p>
      <div className="flex flex-wrap items-center gap-1.5 text-sm">
        {chain.map((doc, i) => (
          <span key={doc.id} className="flex items-center gap-1.5">
            <span
              className={cn(
                "rounded border px-2 py-0.5 font-mono text-xs",
                doc.status === "superseded" && "text-muted-foreground line-through",
                doc.document_type === "credit_note" && "border-warning/50 text-warning",
                i === chain.length - 1 && doc.status !== "superseded" && "border-positive/50 text-positive"
              )}
            >
              {doc.number}
            </span>
            {i < chain.length - 1 && <ArrowRight className="h-3.5 w-3.5 text-muted-foreground" />}
          </span>
        ))}
      </div>
    </div>
  );
}
