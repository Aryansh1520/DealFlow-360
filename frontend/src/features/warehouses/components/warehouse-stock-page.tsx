"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft, Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/layout/page-header";
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
import { useAllProducts } from "@/features/catalog/hooks";
import { useAdjustStock, useAllWarehouses, useWarehouseStock } from "@/features/warehouses/hooks";

const adjustSchema = z.object({
  product_id: z.string().min(1, "Select a product"),
  delta: z.coerce.number().int().refine((value) => value !== 0, "Delta cannot be zero"),
  reason: z.string().min(1, "Reason is required"),
});

type AdjustValues = z.infer<typeof adjustSchema>;

/** A standalone page — was previously a modal (`WarehouseStockDialog`), now
 * its own route (`/config/warehouses/{id}`) so a warehouse's stock is a real,
 * bookmarkable/linkable place rather than transient dialog state. */
export function WarehouseStockPage({ warehouseId }: { warehouseId: number }) {
  const router = useRouter();
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("warehouses:write");

  // No single-warehouse GET is wired up on the frontend yet — reuse the same
  // unpaginated list the rest of this feature already fetches for pickers.
  const { data: warehousesPage, isLoading: warehouseLoading } = useAllWarehouses();
  const warehouse = warehousesPage?.items.find((item) => item.id === warehouseId) ?? null;

  const { data: stock, isLoading: stockLoading } = useWarehouseStock(warehouseId);
  const { data: productsPage } = useAllProducts();
  const adjustStock = useAdjustStock();

  const form = useForm<AdjustValues>({
    resolver: zodResolver(adjustSchema),
    defaultValues: { product_id: "", delta: 0, reason: "" },
  });

  const onSubmit = async (values: AdjustValues) => {
    await adjustStock.mutateAsync({
      product_id: Number(values.product_id),
      warehouse_id: warehouseId,
      delta: values.delta,
      reason: values.reason,
    });
    form.reset({ product_id: "", delta: 0, reason: "" });
  };

  const backButton = (
    <Button variant="outline" onClick={() => router.push("/config/warehouses")}>
      <ArrowLeft />
      Back to warehouses
    </Button>
  );

  if (!warehouseLoading && !warehouse) {
    return (
      <div className="space-y-4">
        <PageHeader title="Warehouse not found" actions={backButton} />
        <Alert variant="destructive">
          <AlertTitle>Warehouse not found</AlertTitle>
          <AlertDescription>This warehouse may have been deleted.</AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {warehouseLoading ? (
        <div className="mb-6 flex items-center justify-between border-b pb-6">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-10 w-40" />
        </div>
      ) : (
        <PageHeader
          title={`${warehouse!.name} · Stock`}
          description="On-hand and reserved units at this warehouse."
          actions={backButton}
        />
      )}

      {canWrite && warehouse && (
        <div className="rounded-lg border bg-card p-4 shadow-sm">
          <Form {...form}>
            <form
              onSubmit={form.handleSubmit(onSubmit)}
              className="grid grid-cols-1 items-end gap-3 sm:grid-cols-[1fr_auto_1.5fr_auto]"
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
        </div>
      )}

      <div className="rounded-lg border bg-card shadow-sm">
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
            {stockLoading ? (
              Array.from({ length: 5 }).map((_, index) => (
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
                <TableCell colSpan={4} className="h-24 text-center text-muted-foreground">
                  No stock recorded for this warehouse yet.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
