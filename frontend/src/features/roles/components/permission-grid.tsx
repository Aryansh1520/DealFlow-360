"use client";

import * as React from "react";

import { Checkbox } from "@/components/ui/checkbox";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { PermissionResourceRead } from "@/lib/api/types";
import { PERMISSION_ACTION_LABELS, PERMISSION_ACTION_ORDER } from "@/features/roles/permission-copy";

interface PermissionGridProps {
  resources: PermissionResourceRead[];
  /** Granted permission strings, e.g. `["quotations:read", "quotations:write"]` —
   * or `["*"]` for "grant everything". Same shape the API expects, so callers
   * don't need a separate conversion step. */
  value: string[];
  onChange: (next: string[]) => void;
  disabled?: boolean;
}

/** A resource × action checkbox grid — replaces asking an admin to type
 * `quotations:write` by hand. Every row/column comes from `GET /meta/enums`'s
 * `permission_resources`, so a new permission the backend starts enforcing
 * shows up here automatically, with no frontend change. */
export function PermissionGrid({ resources, value, onChange, disabled }: PermissionGridProps) {
  const wildcard = value.includes("*");
  const selected = React.useMemo(() => new Set(value), [value]);

  const columns = PERMISSION_ACTION_ORDER.filter((action) =>
    resources.some((resource) => resource.actions.includes(action))
  );

  const togglePermission = (permission: string, checked: boolean) => {
    const next = new Set(selected);
    if (checked) next.add(permission);
    else next.delete(permission);
    onChange(Array.from(next));
  };

  return (
    <div className="space-y-3">
      <label className="flex items-center gap-2 rounded-md border bg-muted/30 p-2.5 text-sm">
        <Checkbox
          checked={wildcard}
          disabled={disabled}
          onCheckedChange={(checked) => onChange(checked === true ? ["*"] : [])}
        />
        <span>
          <span className="font-medium">Grant everything</span>
          <span className="text-muted-foreground"> — full access to every resource and action.</span>
        </span>
      </label>

      {!wildcard && (
        <div className="max-h-72 overflow-y-auto rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Resource</TableHead>
                {columns.map((action) => (
                  <TableHead key={action} className="w-24 text-center">
                    {PERMISSION_ACTION_LABELS[action] ?? action}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {resources.map((resource) => (
                <TableRow key={resource.resource}>
                  <TableCell className="font-medium">{resource.label}</TableCell>
                  {columns.map((action) => {
                    const supported = resource.actions.includes(action);
                    const permission = `${resource.resource}:${action}`;
                    return (
                      <TableCell key={action} className="text-center">
                        {supported ? (
                          <Checkbox
                            checked={selected.has(permission)}
                            disabled={disabled}
                            onCheckedChange={(checked) => togglePermission(permission, checked === true)}
                            aria-label={`${resource.label} — ${PERMISSION_ACTION_LABELS[action] ?? action}`}
                          />
                        ) : (
                          <span className="text-muted-foreground/40">—</span>
                        )}
                      </TableCell>
                    );
                  })}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
