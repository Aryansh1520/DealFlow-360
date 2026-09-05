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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { PriceListRead } from "@/lib/api/types";
import { useEnums } from "@/features/meta/hooks";
import { useCreatePriceList, useUpdatePriceList } from "@/features/pricing/hooks";

const NO_TIER = "none";

const priceListSchema = z.object({
  name: z.string().min(1, "Name is required"),
  tier: z.string(),
  currency: z.string().length(3, "3-letter currency code"),
  is_default: z.boolean(),
});

type PriceListValues = z.infer<typeof priceListSchema>;

interface PriceListFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  priceList?: PriceListRead | null;
}

export function PriceListFormDialog({ open, onOpenChange, priceList }: PriceListFormDialogProps) {
  const isEdit = Boolean(priceList);
  const { data: enums } = useEnums();
  const createPriceList = useCreatePriceList();
  const updatePriceList = useUpdatePriceList();

  const form = useForm<PriceListValues>({
    resolver: zodResolver(priceListSchema),
    defaultValues: { name: "", tier: NO_TIER, currency: "INR", is_default: false },
  });

  React.useEffect(() => {
    if (open) {
      form.reset({
        name: priceList?.name ?? "",
        tier: priceList?.tier ?? NO_TIER,
        currency: priceList?.currency ?? "INR",
        is_default: priceList?.is_default ?? false,
      });
    }
  }, [open, priceList, form]);

  const onSubmit = async (values: PriceListValues) => {
    const payload = {
      name: values.name,
      tier: values.tier === NO_TIER ? null : (values.tier as "bronze" | "silver" | "gold"),
      currency: values.currency.toUpperCase(),
      is_default: values.is_default,
    };

    if (isEdit && priceList) {
      await updatePriceList.mutateAsync({ id: priceList.id, payload });
    } else {
      await createPriceList.mutateAsync(payload);
    }
    onOpenChange(false);
  };

  const isPending = createPriceList.isPending || updatePriceList.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEdit ? "Edit price list" : "New price list"}</DialogTitle>
          <DialogDescription>
            {isEdit
              ? "Update this price list's details."
              : "Price lists resolve list price overrides per customer tier."}
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
            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="tier"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Tier</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value={NO_TIER}>Any tier</SelectItem>
                        {(enums?.customer_tier ?? []).map((tier) => (
                          <SelectItem key={tier} value={tier} className="capitalize">
                            {enums?.labels.customer_tier?.[tier] ?? tier}
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
                name="currency"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Currency</FormLabel>
                    <FormControl>
                      <Input {...field} className="uppercase" maxLength={3} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
            <FormField
              control={form.control}
              name="is_default"
              render={({ field }) => (
                <FormItem className="flex flex-row items-center gap-2 space-y-0">
                  <FormControl>
                    <Checkbox checked={field.value} onCheckedChange={field.onChange} />
                  </FormControl>
                  <FormLabel className="font-normal">
                    Default list (used when no tier-specific list matches)
                  </FormLabel>
                </FormItem>
              )}
            />
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={isPending}>
                {isPending && <Loader2 className="animate-spin" />}
                {isEdit ? "Save changes" : "Create price list"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
