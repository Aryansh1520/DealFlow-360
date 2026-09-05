"use client";

import * as React from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
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
import type { WarehouseRead } from "@/lib/api/types";
import { useCreateWarehouse, useUpdateWarehouse } from "@/features/warehouses/hooks";

const warehouseSchema = z.object({
  name: z.string().min(1, "Name is required"),
  code: z.string().min(1, "Code is required"),
  address: z.string(),
  shipping_cost_weight: z.coerce.number().int().min(1).max(100),
  replenishment_threshold: z.coerce.number().int().min(0),
  is_active: z.boolean(),
});

type WarehouseValues = z.infer<typeof warehouseSchema>;

interface WarehouseFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  warehouse?: WarehouseRead | null;
}

export function WarehouseFormDialog({ open, onOpenChange, warehouse }: WarehouseFormDialogProps) {
  const isEdit = Boolean(warehouse);
  const createWarehouse = useCreateWarehouse();
  const updateWarehouse = useUpdateWarehouse();

  const form = useForm<WarehouseValues>({
    resolver: zodResolver(warehouseSchema),
    defaultValues: {
      name: "",
      code: "",
      address: "",
      shipping_cost_weight: 50,
      replenishment_threshold: 0,
      is_active: true,
    },
  });

  React.useEffect(() => {
    if (open) {
      form.reset({
        name: warehouse?.name ?? "",
        code: warehouse?.code ?? "",
        address: warehouse?.address ?? "",
        shipping_cost_weight: warehouse?.shipping_cost_weight ?? 50,
        replenishment_threshold: warehouse?.replenishment_threshold ?? 0,
        is_active: warehouse?.is_active ?? true,
      });
    }
  }, [open, warehouse, form]);

  const onSubmit = async (values: WarehouseValues) => {
    const payload = { ...values, address: values.address || null };

    if (isEdit && warehouse) {
      await updateWarehouse.mutateAsync({ id: warehouse.id, payload });
    } else {
      await createWarehouse.mutateAsync(payload);
    }
    onOpenChange(false);
  };

  const isPending = createWarehouse.isPending || updateWarehouse.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEdit ? "Edit warehouse" : "New warehouse"}</DialogTitle>
          <DialogDescription>
            {isEdit ? "Update the warehouse's details." : "Add a new fulfilment location."}
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
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
                name="code"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Code</FormLabel>
                    <FormControl>
                      <Input {...field} className="uppercase" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
            <FormField
              control={form.control}
              name="address"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Address (optional)</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="shipping_cost_weight"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Shipping cost weight (1–100)</FormLabel>
                    <FormControl>
                      <Input type="number" min={1} max={100} {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="replenishment_threshold"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Replenishment threshold</FormLabel>
                    <FormControl>
                      <Input type="number" min={0} {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
            <FormField
              control={form.control}
              name="is_active"
              render={({ field }) => (
                <FormItem className="flex flex-row items-center gap-2 space-y-0">
                  <FormControl>
                    <Checkbox checked={field.value} onCheckedChange={field.onChange} />
                  </FormControl>
                  <FormLabel className="font-normal">Active</FormLabel>
                </FormItem>
              )}
            />
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={isPending}>
                {isPending && <Loader2 className="animate-spin" />}
                {isEdit ? "Save changes" : "Create warehouse"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
