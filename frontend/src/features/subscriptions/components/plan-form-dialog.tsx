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
import type { SubscriptionPlanRead } from "@/lib/api/types";
import { useEnums } from "@/features/meta/hooks";
import {
  useCreateSubscriptionPlan,
  useUpdateSubscriptionPlan,
} from "@/features/subscriptions/hooks";

const REFUND_POLICIES = ["prorated", "none", "credit_note"] as const;

const planSchema = z.object({
  name: z.string().min(1, "Name is required"),
  interval: z.string().min(1, "Interval is required"),
  billing_cycles: z.string(),
  proration_enabled: z.boolean(),
  cancellation_notice_days: z.coerce.number().int().min(0),
  refund_policy: z.enum(REFUND_POLICIES),
});

type PlanValues = z.infer<typeof planSchema>;

interface PlanFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  plan?: SubscriptionPlanRead | null;
}

export function PlanFormDialog({ open, onOpenChange, plan }: PlanFormDialogProps) {
  const isEdit = Boolean(plan);
  const { data: enums } = useEnums();
  const createPlan = useCreateSubscriptionPlan();
  const updatePlan = useUpdateSubscriptionPlan();

  const form = useForm<PlanValues>({
    resolver: zodResolver(planSchema),
    defaultValues: {
      name: "",
      interval: "monthly",
      billing_cycles: "",
      proration_enabled: true,
      cancellation_notice_days: 0,
      refund_policy: "prorated",
    },
  });

  React.useEffect(() => {
    if (open) {
      form.reset({
        name: plan?.name ?? "",
        interval: plan?.interval ?? "monthly",
        billing_cycles: plan?.billing_cycles != null ? String(plan.billing_cycles) : "",
        proration_enabled: plan?.proration_enabled ?? true,
        cancellation_notice_days: plan?.cancellation_notice_days ?? 0,
        refund_policy: plan?.refund_policy ?? "prorated",
      });
    }
  }, [open, plan, form]);

  const onSubmit = async (values: PlanValues) => {
    const payload = {
      name: values.name,
      interval: values.interval as "monthly" | "quarterly" | "yearly",
      billing_cycles: values.billing_cycles ? Number(values.billing_cycles) : null,
      proration_enabled: values.proration_enabled,
      cancellation_notice_days: values.cancellation_notice_days,
      refund_policy: values.refund_policy,
    };

    if (isEdit && plan) {
      await updatePlan.mutateAsync({ id: plan.id, payload });
    } else {
      await createPlan.mutateAsync(payload);
    }
    onOpenChange(false);
  };

  const isPending = createPlan.isPending || updatePlan.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEdit ? "Edit plan" : "New subscription plan"}</DialogTitle>
          <DialogDescription>
            {isEdit ? "Update the plan's billing terms." : "Define a recurring billing plan."}
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
                name="interval"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Billing interval</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {(enums?.billing_interval ?? ["monthly", "quarterly", "yearly"]).map(
                          (interval) => (
                            <SelectItem key={interval} value={interval}>
                              {enums?.labels.billing_interval?.[interval] ?? interval}
                            </SelectItem>
                          )
                        )}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="billing_cycles"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Billing cycles (optional)</FormLabel>
                    <FormControl>
                      <Input type="number" min={1} placeholder="Unlimited" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="cancellation_notice_days"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Cancellation notice (days)</FormLabel>
                    <FormControl>
                      <Input type="number" min={0} {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="refund_policy"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Refund policy</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="prorated">Prorated</SelectItem>
                        <SelectItem value="none">None</SelectItem>
                        <SelectItem value="credit_note">Credit note</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
            <FormField
              control={form.control}
              name="proration_enabled"
              render={({ field }) => (
                <FormItem className="flex flex-row items-center gap-2 space-y-0">
                  <FormControl>
                    <Checkbox checked={field.value} onCheckedChange={field.onChange} />
                  </FormControl>
                  <FormLabel className="font-normal">Proration enabled</FormLabel>
                </FormItem>
              )}
            />
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={isPending}>
                {isPending && <Loader2 className="animate-spin" />}
                {isEdit ? "Save changes" : "Create plan"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
