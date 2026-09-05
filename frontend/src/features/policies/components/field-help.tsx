import type { ReactNode } from "react";
import { Info } from "lucide-react";

import { Label } from "@/components/ui/label";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

/** A labelled field with its explanation surfaced entirely via the (i) icon's
 * hover/focus tooltip — `FRONTEND_PHASE_1.md` Task 7: "the approver-facing
 * vocabulary matters." Pulled from `DECISION_ENGINE.md` §2/§3, and shared
 * verbatim from `field-copy.ts` between `PolicyForm` (editable) and
 * `PolicyView` (read-only) so the two modes never say something different
 * about the same field. There's no separate helper-text line below the
 * field — the tooltip is the one explanation, in both modes. */
export function FieldHelp({
  label,
  tooltip,
  children,
}: {
  label: string;
  tooltip: string;
  children: ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-1.5">
        <Label>{label}</Label>
        <Tooltip delayDuration={200}>
          <TooltipTrigger asChild>
            <button
              type="button"
              className="text-muted-foreground/70 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-full"
              aria-label={`What does "${label}" mean?`}
            >
              <Info className="h-3.5 w-3.5" />
            </button>
          </TooltipTrigger>
          <TooltipContent>{tooltip}</TooltipContent>
        </Tooltip>
      </div>
      {children}
    </div>
  );
}
