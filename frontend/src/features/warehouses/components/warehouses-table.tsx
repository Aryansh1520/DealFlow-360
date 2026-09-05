"use client";

import * as React from "react";
import { Boxes, ChevronLeft, ChevronRight, MoreHorizontal, Plus } from "lucide-react";

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
import type { WarehouseRead } from "@/lib/api/types";
import { WarehouseFormDialog } from "@/features/warehouses/components/warehouse-form-dialog";
import { WarehouseStockDialog } from "@/features/warehouses/components/warehouse-stock-dialog";
import { useDeleteWarehouse, useWarehouses } from "@/features/warehouses/hooks";

const PAGE_SIZE = 10;

export function WarehousesTable() {
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("warehouses:write");

  const [page, setPage] = React.useState(1);
  const [formOpen, setFormOpen] = React.useState(false);
  const [editingWarehouse, setEditingWarehouse] = React.useState<WarehouseRead | null>(null);
  const [deletingWarehouse, setDeletingWarehouse] = React.useState<WarehouseRead | null>(null);
  const [stockWarehouse, setStockWarehouse] = React.useState<WarehouseRead | null>(null);

  const { data, isLoading, isError, error } = useWarehouses({ page, page_size: PAGE_SIZE });
  const deleteWarehouse = useDeleteWarehouse();

  const openCreate = () => {
    setEditingWarehouse(null);
    setFormOpen(true);
  };

  const openEdit = (warehouse: WarehouseRead) => {
    setEditingWarehouse(warehouse);
    setFormOpen(true);
  };

  if (isError) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Failed to load warehouses</AlertTitle>
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
            Add warehouse
          </Button>
        )}
      </div>

      <div className="rounded-lg border bg-card shadow-sm">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Code</TableHead>
              <TableHead>Shipping cost / kg</TableHead>
              <TableHead>Replenishment threshold</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="w-[50px]" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 3 }).map((_, index) => (
                <TableRow key={index}>
                  {Array.from({ length: 6 }).map((__, cell) => (
                    <TableCell key={cell}>
                      <Skeleton className="h-4 w-20" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : data && data.items.length > 0 ? (
              data.items.map((warehouse) => (
                <TableRow key={warehouse.id}>
                  <TableCell>
                    <p className="font-medium">{warehouse.name}</p>
                    {warehouse.address && (
                      <p className="text-xs text-muted-foreground">{warehouse.address}</p>
                    )}
                  </TableCell>
                  <TableCell className="font-mono text-xs">{warehouse.code}</TableCell>
                  <TableCell className="tabular-nums">{warehouse.shipping_cost_weight}</TableCell>
                  <TableCell className="tabular-nums">
                    {warehouse.replenishment_threshold}
                  </TableCell>
                  <TableCell>
                    <Badge variant={warehouse.is_active ? "positive" : "outline"}>
                      {warehouse.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon">
                          <MoreHorizontal />
                          <span className="sr-only">Open actions</span>
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => setStockWarehouse(warehouse)}>
                          <Boxes />
                          View stock
                        </DropdownMenuItem>
                        {canWrite && (
                          <>
                            <DropdownMenuItem onClick={() => openEdit(warehouse)}>
                              Edit
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              className="text-destructive focus:text-destructive"
                              onClick={() => setDeletingWarehouse(warehouse)}
                            >
                              Delete
                            </DropdownMenuItem>
                          </>
                        )}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={6} className="h-24 text-center text-muted-foreground">
                  No warehouses yet.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {data && data.pages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Page {data.page} of {data.pages} · {data.total} warehouses
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

      <WarehouseFormDialog open={formOpen} onOpenChange={setFormOpen} warehouse={editingWarehouse} />
      <WarehouseStockDialog warehouse={stockWarehouse} onClose={() => setStockWarehouse(null)} />
      <ConfirmDeleteDialog
        open={Boolean(deletingWarehouse)}
        onOpenChange={(open) => !open && setDeletingWarehouse(null)}
        title="Delete warehouse"
        description={
          <>
            This will permanently delete <strong>{deletingWarehouse?.name}</strong>. This action
            cannot be undone.
          </>
        }
        onConfirm={() => deletingWarehouse && deleteWarehouse.mutateAsync(deletingWarehouse.id)}
        isPending={deleteWarehouse.isPending}
      />
    </div>
  );
}
