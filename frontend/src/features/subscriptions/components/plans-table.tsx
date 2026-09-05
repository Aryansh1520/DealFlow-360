"use client";

import * as React from "react";
import { ChevronLeft, ChevronRight, MoreHorizontal, Plus } from "lucide-react";

import { getErrorMessage } from "@/lib/api-client";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfirmDeleteDialog } from "@/components/ui/confirm-delete-dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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
import { useEnums } from "@/features/meta/hooks";
import type { SubscriptionPlanRead } from "@/lib/api/types";
import { PlanFormDialog } from "@/features/subscriptions/components/plan-form-dialog";
import { useDeleteSubscriptionPlan, useSubscriptionPlans } from "@/features/subscriptions/hooks";

const PAGE_SIZE = 10;

export function PlansTable() {
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("subscriptions:write");
  const { data: enums } = useEnums();

  const [page, setPage] = React.useState(1);
  const [formOpen, setFormOpen] = React.useState(false);
  const [editingPlan, setEditingPlan] = React.useState<SubscriptionPlanRead | null>(null);
  const [deletingPlan, setDeletingPlan] = React.useState<SubscriptionPlanRead | null>(null);

  const { data, isLoading, isError, error } = useSubscriptionPlans({
    page,
    page_size: PAGE_SIZE,
  });
  const deletePlan = useDeleteSubscriptionPlan();

  const openCreate = () => {
    setEditingPlan(null);
    setFormOpen(true);
  };

  const openEdit = (plan: SubscriptionPlanRead) => {
    setEditingPlan(plan);
    setFormOpen(true);
  };

  if (isError) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Failed to load subscription plans</AlertTitle>
        <AlertDescription>{getErrorMessage(error)}</AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-end">
        {canWrite && (
          <Button onClick={openCreate}>
            <Plus />
            Add plan
          </Button>
        )}
      </div>

      <div className="rounded-lg border bg-card shadow-sm">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Interval</TableHead>
              <TableHead>Cycles</TableHead>
              <TableHead>Proration</TableHead>
              <TableHead>Cancellation notice</TableHead>
              <TableHead>Refund policy</TableHead>
              {canWrite && <TableHead className="w-[50px]" />}
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 4 }).map((_, index) => (
                <TableRow key={index}>
                  {Array.from({ length: canWrite ? 7 : 6 }).map((__, cell) => (
                    <TableCell key={cell}>
                      <Skeleton className="h-4 w-20" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : data && data.items.length > 0 ? (
              data.items.map((plan) => (
                <TableRow key={plan.id}>
                  <TableCell className="font-medium">{plan.name}</TableCell>
                  <TableCell className="capitalize">
                    {enums?.labels.billing_interval?.[plan.interval] ?? plan.interval}
                  </TableCell>
                  <TableCell>{plan.billing_cycles ?? "Unlimited"}</TableCell>
                  <TableCell>
                    <Badge variant={plan.proration_enabled ? "positive" : "outline"}>
                      {plan.proration_enabled ? "Enabled" : "Disabled"}
                    </Badge>
                  </TableCell>
                  <TableCell>{plan.cancellation_notice_days} days</TableCell>
                  <TableCell className="capitalize">
                    {plan.refund_policy.replace("_", " ")}
                  </TableCell>
                  {canWrite && (
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreHorizontal />
                            <span className="sr-only">Open actions</span>
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => openEdit(plan)}>Edit</DropdownMenuItem>
                          <DropdownMenuItem
                            className="text-destructive focus:text-destructive"
                            onClick={() => setDeletingPlan(plan)}
                          >
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  )}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={canWrite ? 7 : 6} className="h-24 text-center text-muted-foreground">
                  No subscription plans yet.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {data && data.pages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Page {data.page} of {data.pages} · {data.total} plans
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((current) => current - 1)}
            >
              <ChevronLeft />
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= data.pages}
              onClick={() => setPage((current) => current + 1)}
            >
              Next
              <ChevronRight />
            </Button>
          </div>
        </div>
      )}

      <PlanFormDialog open={formOpen} onOpenChange={setFormOpen} plan={editingPlan} />
      <ConfirmDeleteDialog
        open={Boolean(deletingPlan)}
        onOpenChange={(open) => !open && setDeletingPlan(null)}
        title="Delete subscription plan"
        description={
          <>
            This will permanently delete <strong>{deletingPlan?.name}</strong>. This action
            cannot be undone.
          </>
        }
        onConfirm={() => deletingPlan && deletePlan.mutateAsync(deletingPlan.id)}
        isPending={deletePlan.isPending}
      />
    </div>
  );
}
