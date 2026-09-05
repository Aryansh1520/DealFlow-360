import type { ReactNode } from "react";
import { Info } from "lucide-react";

import { Label } from "@/components/ui/label";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

/** A labelled field with a one-line explanation in the approver's own
 * vocabulary — `FRONTEND_PHASE_1.md` Task 7: "the approver-facing vocabulary
 * matters." Pulled from `DECISION_ENGINE.md` §2/§3.
 *
 * `tooltip` is a longer, example-driven explanation surfaced on hover/focus of
 * the (i) icon — for readers who want the "so what does changing this do"
 * version, not just the one-line caption. Falls back to `help` when omitted. */
export function FieldHelp({
  label,
  help,
  tooltip,
  children,
}: {
  label: string;
  help: string;
  tooltip?: string;
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
          <TooltipContent>{tooltip ?? help}</TooltipContent>
        </Tooltip>
      </div>
      {children}
      <p className="text-xs text-muted-foreground">{help}</p>
    </div>
  );
}
