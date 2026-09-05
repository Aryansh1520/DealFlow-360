"use client";

import * as React from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
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
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useCustomers } from "@/features/customers/hooks";
import { useCreateQuotation } from "@/features/quotations/hooks";

const schema = z.object({ customer_id: z.string().min(1, "Select a customer") });
type Values = z.infer<typeof schema>;

interface CreateQuotationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CreateQuotationDialog({ open, onOpenChange }: CreateQuotationDialogProps) {
  const router = useRouter();
  const { data: customersPage } = useCustomers({ page: 1, page_size: 100 });
  const createQuotation = useCreateQuotation();

  const form = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { customer_id: "" } });

  React.useEffect(() => {
    if (open) form.reset({ customer_id: "" });
  }, [open, form]);

  const onSubmit = async (values: Values) => {
    const quotation = await createQuotation.mutateAsync({ customer_id: Number(values.customer_id) });
    onOpenChange(false);
    router.push(`/workspace/quotations/${quotation.id}`);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New quotation</DialogTitle>
          <DialogDescription>Pick a customer to start building.</DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="customer_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Customer</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select a customer" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {customersPage?.items.map((customer) => (
                        <SelectItem key={customer.id} value={String(customer.id)}>
                          {customer.name} · <span className="capitalize">{customer.tier}</span>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={createQuotation.isPending}>
                {createQuotation.isPending && <Loader2 className="animate-spin" />}
                Create
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
