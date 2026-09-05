"use client";

import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { useDecisionTrace } from "@/features/quotations/hooks";
import { DecisionTracePanel } from "@/features/approvals/components/decision-trace";

interface DecisionTraceDrawerProps {
  quotationId: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/** The builder's "why?" link opens this — same `DecisionTracePanel` the
 * approvals screen renders inline, so rep and approver see identical numbers. */
export function DecisionTraceDrawer({ quotationId, open, onOpenChange }: DecisionTraceDrawerProps) {
  const { data: trace, isLoading } = useDecisionTrace(quotationId, open);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-xl">
        <SheetHeader>
          <SheetTitle>Why does this need approval?</SheetTitle>
          <SheetDescription>
            Every number below is computed by the decision engine — nothing here is derived
            client-side.
          </SheetDescription>
        </SheetHeader>
        <div className="mt-6">
          {isLoading || !trace ? (
            <div className="space-y-4">
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-48 w-full" />
            </div>
          ) : (
            <DecisionTracePanel trace={trace} />
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
