"use client";

import * as React from "react";
import { ChevronDown, Plus, Search } from "lucide-react";

import { getErrorMessage } from "@/lib/api-client";
import { useDebounce } from "@/lib/use-debounce";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useAuth } from "@/features/auth/auth-context";
import type { Role } from "@/features/auth/types";
import { useEnums } from "@/features/meta/hooks";
import { useRoles } from "@/features/roles/hooks";
import { DeleteRoleDialog } from "@/features/roles/components/delete-role-dialog";
import { PermissionSummaryTable } from "@/features/roles/components/permission-summary-table";
import { RoleFormDialog } from "@/features/roles/components/role-form-dialog";

export function RolesTable() {
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("roles:write");

  const [searchInput, setSearchInput] = React.useState("");
  const search = useDebounce(searchInput);

  const [formOpen, setFormOpen] = React.useState(false);
  const [editingRole, setEditingRole] = React.useState<Role | null>(null);
  const [deletingRole, setDeletingRole] = React.useState<Role | null>(null);

  const { data, isLoading, isError, error } = useRoles({
    page_size: 100,
    search: search || undefined,
  });

  const openCreate = () => {
    setEditingRole(null);
    setFormOpen(true);
  };

  const openEdit = (role: Role) => {
    setEditingRole(role);
    setFormOpen(true);
  };

  if (isError) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Failed to load roles</AlertTitle>
        <AlertDescription>{getErrorMessage(error)}</AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <div className="relative w-full max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search roles..."
            className="pl-9"
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
          />
        </div>
        {canWrite && (
          <Button onClick={openCreate}>
            <Plus />
            Add role
          </Button>
        )}
      </div>

      <div className="rounded-lg border bg-card shadow-sm">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Description</TableHead>
              <TableHead>Permissions</TableHead>
              {canWrite && <TableHead className="w-[100px]">Actions</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 3 }).map((_, index) => (
                <TableRow key={index}>
                  <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                  <TableCell><Skeleton className="h-4 w-40" /></TableCell>
                  <TableCell><Skeleton className="h-5 w-32" /></TableCell>
                  {canWrite && <TableCell />}
                </TableRow>
              ))
            ) : data && data.items.length > 0 ? (
              data.items.map((role) => (
                <TableRow key={role.id}>
                  <TableCell className="font-medium">{role.name}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {role.description || "—"}
                  </TableCell>
                  <TableCell>
                    <PermissionsCell role={role} />
                  </TableCell>
                  {canWrite && (
                    <TableCell>
                      <div className="flex gap-2">
                        <Button variant="ghost" size="sm" onClick={() => openEdit(role)}>
                          Edit
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-destructive hover:text-destructive"
                          onClick={() => setDeletingRole(role)}
                        >
                          Delete
                        </Button>
                      </div>
                    </TableCell>
                  )}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={canWrite ? 4 : 3} className="h-24 text-center text-muted-foreground">
                  No roles found.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      <RoleFormDialog open={formOpen} onOpenChange={setFormOpen} role={editingRole} />
      <DeleteRoleDialog role={deletingRole} onClose={() => setDeletingRole(null)} />
    </div>
  );
}

/** Click-to-toggle summary — replaces a wall of raw `quotations:write`-style
 * badges. Collapsed state is just a count (or "Full access" for `*`); opening
 * it shows the same resource × action table `PermissionGrid` edits from,
 * read-only, so a role's permissions always read the same way whether you're
 * viewing or editing them. */
function PermissionsCell({ role }: { role: Role }) {
  const { data: enums } = useEnums();
  const resources = enums?.permission_resources ?? [];
  const wildcard = role.permissions.includes("*");

  if (role.permissions.length === 0) {
    return <span className="text-muted-foreground">—</span>;
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          className="inline-flex items-center gap-1 rounded-md border bg-muted/40 px-2 py-1 text-xs font-medium transition-colors hover:bg-muted"
        >
          {wildcard ? "Full access" : `${role.permissions.length} permission${role.permissions.length === 1 ? "" : "s"}`}
          <ChevronDown className="h-3 w-3" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-auto p-3">
        {wildcard ? (
          <p className="max-w-56 text-sm text-muted-foreground">
            This role has full access — every resource and action.
          </p>
        ) : (
          <PermissionSummaryTable resources={resources} granted={role.permissions} />
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
