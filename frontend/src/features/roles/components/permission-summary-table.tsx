import { Check } from "lucide-react";

import type { PermissionResourceRead } from "@/lib/api/types";
import { PERMISSION_ACTION_LABELS, PERMISSION_ACTION_ORDER } from "@/features/roles/permission-copy";

interface PermissionSummaryTableProps {
  resources: PermissionResourceRead[];
  /** Granted permission strings, e.g. `["quotations:read", "quotations:write"]`. */
  granted: string[];
}

/** Read-only mirror of `PermissionGrid` — same rows, same columns, a
 * checkmark instead of a checkbox. Only resources with at least one granted
 * action are shown, so a role with a handful of permissions doesn't render
 * every resource in the system just to show mostly blank rows. */
export function PermissionSummaryTable({ resources, granted }: PermissionSummaryTableProps) {
  const grantedSet = new Set(granted);
  const columns = PERMISSION_ACTION_ORDER.filter((action) =>
    resources.some((resource) => resource.actions.includes(action))
  );
  const relevant = resources.filter((resource) =>
    resource.actions.some((action) => grantedSet.has(`${resource.resource}:${action}`))
  );

  if (relevant.length === 0) {
    return <p className="text-sm text-muted-foreground">No permissions granted.</p>;
  }

  return (
    <table className="border-collapse text-sm">
      <thead>
        <tr>
          <th className="px-2 pb-1.5 text-left font-medium text-muted-foreground">Resource</th>
          {columns.map((action) => (
            <th key={action} className="px-2 pb-1.5 text-center font-medium text-muted-foreground">
              {PERMISSION_ACTION_LABELS[action] ?? action}
            </th>
          ))}
        </tr>
      </thead>
      <tbody className="divide-y divide-border">
        {relevant.map((resource) => (
          <tr key={resource.resource}>
            <td className="px-2 py-1 pr-4 font-medium">{resource.label}</td>
            {columns.map((action) => {
              const supported = resource.actions.includes(action);
              const isGranted = grantedSet.has(`${resource.resource}:${action}`);
              return (
                <td key={action} className="px-2 py-1 text-center">
                  {supported && isGranted ? (
                    <Check className="mx-auto h-3.5 w-3.5 text-positive" />
                  ) : supported ? (
                    <span className="text-muted-foreground/30">·</span>
                  ) : null}
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
