"use client";

import * as React from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { BpsInput } from "@/components/ui/bps-input";
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
import { MoneyInput } from "@/components/ui/money-input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { PriceListEntryRead, PriceListRead } from "@/lib/api/types";
import { useAllProducts } from "@/features/catalog/hooks";
import { useCreatePriceListEntry, useUpdatePriceListEntry } from "@/features/pricing/hooks";

const NO_OVERRIDE = "no-override";

const entrySchema = z.object({
  product_id: z.string().min(1, "Select a product"),
  override_price_minor: z.coerce.number().int().min(0),
  use_override: z.boolean(),
  extra_discount_bps: z.coerce.number().int().min(0),
});

type EntryValues = z.infer<typeof entrySchema>;

interface EntryFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  priceList: PriceListRead;
  entry?: PriceListEntryRead | null;
}

export function EntryFormDialog({ open, onOpenChange, priceList, entry }: EntryFormDialogProps) {
  const isEdit = Boolean(entry);
  const { data: productsPage } = useAllProducts();
  const createEntry = useCreatePriceListEntry();
  const updateEntry = useUpdatePriceListEntry();

  const form = useForm<EntryValues>({
    resolver: zodResolver(entrySchema),
    defaultValues: {
      product_id: "",
      override_price_minor: 0,
      use_override: false,
      extra_discount_bps: 0,
    },
  });

  const useOverride = form.watch("use_override");

  React.useEffect(() => {
    if (open) {
      form.reset({
        product_id: entry ? String(entry.product_id) : "",
        override_price_minor: entry?.override_price_minor ?? 0,
        use_override: entry?.override_price_minor != null,
        extra_discount_bps: entry?.extra_discount_bps ?? 0,
      });
    }
  }, [open, entry, form]);

  const onSubmit = async (values: EntryValues) => {
    const basePayload = {
      product_id: Number(values.product_id),
      variant_id: null,
      override_price_minor: values.use_override ? values.override_price_minor : null,
      extra_discount_bps: values.extra_discount_bps,
    };

    if (isEdit && entry) {
      await updateEntry.mutateAsync({
        priceListId: priceList.id,
        entryId: entry.id,
        payload: {
          override_price_minor: basePayload.override_price_minor,
          extra_discount_bps: basePayload.extra_discount_bps,
        },
      });
    } else {
      await createEntry.mutateAsync({ priceListId: priceList.id, payload: basePayload });
    }
    onOpenChange(false);
  };

  const isPending = createEntry.isPending || updateEntry.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEdit ? "Edit entry" : "New entry"}</DialogTitle>
          <DialogDescription>
            Override a product's price or add an extra discount within {priceList.name}.
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="product_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Product</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value} disabled={isEdit}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select a product" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {productsPage?.items.map((product) => (
                        <SelectItem key={product.id} value={String(product.id)}>
                          {product.name} · {product.sku}
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
              name="use_override"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Price</FormLabel>
                  <Select
                    onValueChange={(value) => field.onChange(value === "override")}
                    value={field.value ? "override" : NO_OVERRIDE}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value={NO_OVERRIDE}>Use product list price</SelectItem>
                      <SelectItem value="override">Override price</SelectItem>
                    </SelectContent>
                  </Select>
                </FormItem>
              )}
            />
            {useOverride && (
              <FormField
                control={form.control}
                name="override_price_minor"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Override price</FormLabel>
                    <FormControl>
                      <MoneyInput
                        value={field.value}
                        onChange={field.onChange}
                        currency={priceList.currency}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            )}
            <FormField
              control={form.control}
              name="extra_discount_bps"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Extra discount (on top of any order-level discount)</FormLabel>
                  <FormControl>
                    <BpsInput value={field.value} onChange={field.onChange} />
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
                {isEdit ? "Save changes" : "Add entry"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
