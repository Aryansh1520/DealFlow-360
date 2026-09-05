import type { ReactNode } from "react";

import { Label } from "@/components/ui/label";

/** A labelled field with a one-line explanation in the approver's own
 * vocabulary — `FRONTEND_PHASE_1.md` Task 7: "the approver-facing vocabulary
 * matters." Pulled from `DECISION_ENGINE.md` §2/§3. */
export function FieldHelp({
  label,
  help,
  children,
}: {
  label: string;
  help: string;
  children: ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      {children}
      <p className="text-xs text-muted-foreground">{help}</p>
    </div>
  );
}
