"use client";

import * as React from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { Role } from "@/features/auth/types";
import { useEnums } from "@/features/meta/hooks";
import { PermissionGrid } from "@/features/roles/components/permission-grid";
import { useCreateRole, useUpdateRole } from "@/features/roles/hooks";

const DASHBOARD_TYPES = ["super_admin", "sales_manager", "finance_ops", "generic"] as const;
const DASHBOARD_LABELS: Record<string, string> = {
  super_admin: "Super admin",
  sales_manager: "Sales manager",
  finance_ops: "Finance / operations",
  generic: "Generic",
};

const roleSchema = z.object({
  name: z.string().min(1, "Name is required"),
  description: z.string().max(255).optional(),
  permissions: z.array(z.string()),
  dashboard_type: z.enum(DASHBOARD_TYPES),
});

type RoleValues = z.infer<typeof roleSchema>;

interface RoleFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Present when editing; absent when creating. */
  role?: Role | null;
}

export function RoleFormDialog({ open, onOpenChange, role }: RoleFormDialogProps) {
  const isEdit = Boolean(role);
  const createRole = useCreateRole();
  const updateRole = useUpdateRole();
  const { data: enums } = useEnums();
  const resources = enums?.permission_resources ?? [];

  const form = useForm<RoleValues>({
    resolver: zodResolver(roleSchema),
    defaultValues: { name: "", description: "", permissions: [], dashboard_type: "generic" },
  });

  React.useEffect(() => {
    if (open) {
      form.reset({
        name: role?.name ?? "",
        description: role?.description ?? "",
        permissions: role?.permissions ?? [],
        dashboard_type: role?.dashboard_type ?? "generic",
      });
    }
  }, [open, role, form]);

  const onSubmit = async (values: RoleValues) => {
    const payload = {
      name: values.name,
      description: values.description || null,
      permissions: values.permissions,
      dashboard_type: values.dashboard_type,
    };

    if (isEdit && role) {
      await updateRole.mutateAsync({ id: role.id, payload });
    } else {
      await createRole.mutateAsync(payload);
    }
    onOpenChange(false);
  };

  const isPending = createRole.isPending || updateRole.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Edit role" : "New role"}</DialogTitle>
          <DialogDescription>
            {isEdit ? "Update the role's details." : "Create a new role."}
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Name</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="dashboard_type"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Dashboard layout</FormLabel>
                  <FormControl>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {DASHBOARD_TYPES.map((t) => (
                          <SelectItem key={t} value={t}>
                            {DASHBOARD_LABELS[t]}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormControl>
                  <p className="text-xs text-muted-foreground">
                    Which dashboard users with this role land on. Presentation only — it
                    doesn&apos;t change what they can access.
                  </p>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="permissions"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Permissions</FormLabel>
                  <FormControl>
                    <PermissionGrid resources={resources} value={field.value} onChange={field.onChange} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={isPending}>
                {isPending && <Loader2 className="animate-spin" />}
                {isEdit ? "Save changes" : "Create role"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
