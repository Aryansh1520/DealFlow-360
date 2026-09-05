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
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { WarehouseRead } from "@/lib/api/types";
import { useAuth } from "@/features/auth/auth-context";
import { useAllProducts } from "@/features/catalog/hooks";
import { useAdjustStock, useWarehouseStock } from "@/features/warehouses/hooks";

const adjustSchema = z.object({
  product_id: z.string().min(1, "Select a product"),
  delta: z.coerce.number().int().refine((value) => value !== 0, "Delta cannot be zero"),
  reason: z.string().min(1, "Reason is required"),
});

type AdjustValues = z.infer<typeof adjustSchema>;

interface WarehouseStockDialogProps {
  warehouse: WarehouseRead | null;
  onClose: () => void;
}

export function WarehouseStockDialog({ warehouse, onClose }: WarehouseStockDialogProps) {
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("warehouses:write");
  const { data: stock, isLoading } = useWarehouseStock(warehouse?.id ?? null);
  const { data: productsPage } = useAllProducts();
  const adjustStock = useAdjustStock();

  const form = useForm<AdjustValues>({
    resolver: zodResolver(adjustSchema),
    defaultValues: { product_id: "", delta: 0, reason: "" },
  });

  React.useEffect(() => {
    if (warehouse) form.reset({ product_id: "", delta: 0, reason: "" });
  }, [warehouse, form]);

  const onSubmit = async (values: AdjustValues) => {
    if (!warehouse) return;
    await adjustStock.mutateAsync({
      product_id: Number(values.product_id),
      warehouse_id: warehouse.id,
      delta: values.delta,
      reason: values.reason,
    });
    form.reset({ product_id: "", delta: 0, reason: "" });
  };

  return (
    <Dialog open={Boolean(warehouse)} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{warehouse?.name} · Stock</DialogTitle>
          <DialogDescription>On-hand and reserved units at this warehouse.</DialogDescription>
        </DialogHeader>

        {canWrite && (
          <>
            <Form {...form}>
              <form
                onSubmit={form.handleSubmit(onSubmit)}
                className="grid grid-cols-[1fr_auto_1.5fr_auto] items-end gap-2"
              >
                <FormField
                  control={form.control}
                  name="product_id"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Product</FormLabel>
                      <Select onValueChange={field.onChange} value={field.value}>
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {productsPage?.items.map((product) => (
                            <SelectItem key={product.id} value={String(product.id)}>
                              {product.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="delta"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Delta</FormLabel>
                      <FormControl>
                        <Input type="number" className="w-24" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="reason"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Reason</FormLabel>
                      <FormControl>
                        <Input placeholder="Cycle count correction" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <Button type="submit" disabled={adjustStock.isPending}>
                  {adjustStock.isPending && <Loader2 className="animate-spin" />}
                  Adjust
                </Button>
              </form>
            </Form>
            <Separator />
          </>
        )}

        <div className="max-h-96 overflow-auto rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Product</TableHead>
                <TableHead className="text-right">On hand</TableHead>
                <TableHead className="text-right">Reserved</TableHead>
                <TableHead className="text-right">Available</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 3 }).map((_, index) => (
                  <TableRow key={index}>
                    <TableCell colSpan={4}>
                      <Skeleton className="h-4 w-full" />
                    </TableCell>
                  </TableRow>
                ))
              ) : stock && stock.items.length > 0 ? (
                stock.items.map((row) => (
                  <TableRow key={row.product_id}>
                    <TableCell>{row.product_name}</TableCell>
                    <TableCell className="text-right tabular-nums">{row.on_hand}</TableCell>
                    <TableCell className="text-right tabular-nums">{row.reserved}</TableCell>
                    <TableCell className="text-right font-medium tabular-nums">
                      {row.available}
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={4} className="h-20 text-center text-muted-foreground">
                    No stock recorded for this warehouse yet.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </DialogContent>
    </Dialog>
  );
}
