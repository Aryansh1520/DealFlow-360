/**
 * Column order and display labels for the resource × action permission grid,
 * shared between the editable `PermissionGrid` (role-form-dialog) and the
 * read-only summary table (roles-table) so the two never drift.
 *
 * Actions aren't always "read"/"write" — `approvals` uses "l1"/"l2",
 * `reports` uses "read"/"export" — see `app/core/permissions.py` (backend,
 * the source of truth) and `MetaEnums.permission_resources`.
 */
export const PERMISSION_ACTION_ORDER = ["read", "write", "l1", "l2", "export"] as const;

export const PERMISSION_ACTION_LABELS: Record<string, string> = {
  read: "Read",
  write: "Write",
  l1: "L1 Approve",
  l2: "L2 Approve",
  export: "Export",
};
