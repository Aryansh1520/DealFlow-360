"use client";

import * as React from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { BpsInput } from "@/components/ui/bps-input";
import { Button } from "@/components/ui/button";
import { Form, FormControl, FormField, FormItem, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { MoneyInput } from "@/components/ui/money-input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { PolicyRead } from "@/lib/api/types";
import { useCategories } from "@/features/catalog/hooks";
import { useEnums } from "@/features/meta/hooks";
import { FieldHelp } from "@/features/policies/components/field-help";
import { useCreatePolicyVersion } from "@/features/policies/hooks";

const scalarSchema = z.object({
  w_blended_bps: z.coerce.number().int().min(0),
  w_worst_bps: z.coerce.number().int().min(0),
  w_value_bps: z.coerce.number().int().min(0),
  w_margin_bps: z.coerce.number().int().min(0),
  scale_overage_bps: z.coerce.number().int().min(0),
  value_reference_minor: z.coerce.number().int().min(0),
  margin_scale_bps: z.coerce.number().int().min(0),
  t1_l1_required: z.coerce.number().int().min(0).max(100),
  t2_l2_required: z.coerce.number().int().min(0).max(100),
  hard_breach_bps: z.coerce.number().int().min(0),
  finance_value_floor_minor: z.coerce.number().int().min(0),
  upsell_min_margin_bps: z.coerce.number().int().min(0),
  upsell_w_lift_bps: z.coerce.number().int().min(0),
  upsell_w_margin_bps: z.coerce.number().int().min(0),
  upsell_w_promo_bps: z.coerce.number().int().min(0),
  sigma_multiplier_x10: z.coerce.number().min(0),
  min_sample_size: z.coerce.number().int().min(1),
  stalled_after_days: z.coerce.number().int().min(1),
});

type ScalarValues = z.infer<typeof scalarSchema>;

function scalarsFrom(policy: PolicyRead): ScalarValues {
  return {
    w_blended_bps: policy.weights.w_blended_bps,
    w_worst_bps: policy.weights.w_worst_bps,
    w_value_bps: policy.weights.w_value_bps,
    w_margin_bps: policy.weights.w_margin_bps,
    scale_overage_bps: policy.weights.scale_overage_bps,
    value_reference_minor: policy.weights.value_reference_minor,
    margin_scale_bps: policy.weights.margin_scale_bps,
    t1_l1_required: policy.thresholds.t1_l1_required,
    t2_l2_required: policy.thresholds.t2_l2_required,
    hard_breach_bps: policy.thresholds.hard_breach_bps,
    finance_value_floor_minor: policy.thresholds.finance_value_floor_minor,
    upsell_min_margin_bps: policy.upsell.min_margin_bps,
    upsell_w_lift_bps: policy.upsell.w_lift_bps,
    upsell_w_margin_bps: policy.upsell.w_margin_bps,
    upsell_w_promo_bps: policy.upsell.w_promo_bps,
    sigma_multiplier_x10: policy.anomaly.sigma_multiplier_bps / 10000,
    min_sample_size: policy.anomaly.min_sample_size,
    stalled_after_days: policy.stalled_after_days,
  };
}

interface TierRow {
  tier: string;
  ceiling_bps: number;
}

interface CategoryRow {
  category_id: number;
  category_name: string;
  ceiling_bps: number;
  margin_floor_bps: number;
}

interface PolicyFormProps {
  /** The version this draft is seeded from — its values pre-fill every field. */
  source: PolicyRead;
  onCreated: (policy: PolicyRead) => void;
  onCancel: () => void;
}

export function PolicyForm({ source, onCreated, onCancel }: PolicyFormProps) {
  const { data: categoriesPage } = useCategories();
  const { data: enums } = useEnums();
  const createVersion = useCreatePolicyVersion();

  const [tierRows, setTierRows] = React.useState<TierRow[]>([]);

  React.useEffect(() => {
    if (!enums) return;
    setTierRows(
      enums.customer_tier.map((tier) => ({
        tier,
        ceiling_bps: source.tier_ceilings.find((tc) => tc.tier === tier)?.ceiling_bps ?? 0,
      }))
    );
    // Only re-seed when the source version changes — not on every enums refetch.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enums, source.id]);

  const [categoryRows, setCategoryRows] = React.useState<CategoryRow[]>([]);

  React.useEffect(() => {
    if (!categoriesPage) return;
    setCategoryRows(
      categoriesPage.items.map((category) => {
        const existing = source.category_ceilings.find((cc) => cc.category_id === category.id);
        return {
          category_id: category.id,
          category_name: category.name,
          ceiling_bps: existing?.ceiling_bps ?? 0,
          margin_floor_bps: existing?.margin_floor_bps ?? 0,
        };
      })
    );
    // Only re-seed when the source version changes — not on every categories refetch.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [categoriesPage, source.id]);

  const form = useForm<ScalarValues>({
    resolver: zodResolver(scalarSchema),
    defaultValues: scalarsFrom(source),
  });

  const onSubmit = async (values: ScalarValues) => {
    const payload = {
      tier_ceilings: tierRows as { tier: "bronze" | "silver" | "gold"; ceiling_bps: number }[],
      category_ceilings: categoryRows.map(({ category_id, ceiling_bps, margin_floor_bps }) => ({
        category_id,
        ceiling_bps,
        margin_floor_bps,
      })),
      weights: {
        w_blended_bps: values.w_blended_bps,
        w_worst_bps: values.w_worst_bps,
        w_value_bps: values.w_value_bps,
        w_margin_bps: values.w_margin_bps,
        scale_overage_bps: values.scale_overage_bps,
        value_reference_minor: values.value_reference_minor,
        margin_scale_bps: values.margin_scale_bps,
      },
      thresholds: {
        t1_l1_required: values.t1_l1_required,
        t2_l2_required: values.t2_l2_required,
        hard_breach_bps: values.hard_breach_bps,
        finance_value_floor_minor: values.finance_value_floor_minor,
      },
      upsell: {
        min_margin_bps: values.upsell_min_margin_bps,
        w_lift_bps: values.upsell_w_lift_bps,
        w_margin_bps: values.upsell_w_margin_bps,
        w_promo_bps: values.upsell_w_promo_bps,
      },
      anomaly: {
        sigma_multiplier_bps: Math.round(values.sigma_multiplier_x10 * 10000),
        min_sample_size: values.min_sample_size,
      },
      stalled_after_days: values.stalled_after_days,
    };

    const created = await createVersion.mutateAsync(payload);
    onCreated(created);
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
        <section className="space-y-3">
          <div>
            <h3 className="text-sm font-semibold">Tier ceilings</h3>
            <p className="text-xs text-muted-foreground">
              The maximum discount a customer's loyalty tier alone permits.
            </p>
          </div>
          <div className="rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tier</TableHead>
                  <TableHead className="w-40 text-right">Ceiling</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tierRows.map((row) => (
                  <TableRow key={row.tier}>
                    <TableCell className="capitalize">{row.tier}</TableCell>
                    <TableCell className="text-right">
                      <BpsInput
                        value={row.ceiling_bps}
                        onChange={(bps) =>
                          setTierRows((rows) =>
                            rows.map((r) => (r.tier === row.tier ? { ...r, ceiling_bps: bps } : r))
                          )
                        }
                        className="ml-auto w-28"
                      />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </section>

        <section className="space-y-3">
          <div>
            <h3 className="text-sm font-semibold">Category ceilings</h3>
            <p className="text-xs text-muted-foreground">
              The stricter of the tier ceiling and a line's category ceiling always wins —
              a Gold customer allowed 15% is still capped at 10% on a Services line.
            </p>
          </div>
          <div className="rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Category</TableHead>
                  <TableHead className="w-40 text-right">Ceiling</TableHead>
                  <TableHead className="w-40 text-right">Margin floor</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {categoryRows.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={3} className="h-16 text-center text-muted-foreground">
                      No categories yet.
                    </TableCell>
                  </TableRow>
                ) : (
                  categoryRows.map((row) => (
                    <TableRow key={row.category_id}>
                      <TableCell>{row.category_name}</TableCell>
                      <TableCell className="text-right">
                        <BpsInput
                          value={row.ceiling_bps}
                          onChange={(bps) =>
                            setCategoryRows((rows) =>
                              rows.map((r) =>
                                r.category_id === row.category_id
                                  ? { ...r, ceiling_bps: bps }
                                  : r
                              )
                            )
                          }
                          className="ml-auto w-28"
                        />
                      </TableCell>
                      <TableCell className="text-right">
                        <BpsInput
                          value={row.margin_floor_bps}
                          onChange={(bps) =>
                            setCategoryRows((rows) =>
                              rows.map((r) =>
                                r.category_id === row.category_id
                                  ? { ...r, margin_floor_bps: bps }
                                  : r
                              )
                            )
                          }
                          className="ml-auto w-28"
                        />
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </section>

        <section className="space-y-3">
          <div>
            <h3 className="text-sm font-semibold">Weights</h3>
            <p className="text-xs text-muted-foreground">
              How the four risk components combine into the 0–100 score. The four weights
              are basis-point shares — they don't have to sum to exactly 10000, but should.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <FieldHelp label="Blended overage weight" help="Revenue-weighted average overage across all lines.">
              <FormField
                control={form.control}
                name="w_blended_bps"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <BpsInput value={field.value} onChange={field.onChange} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </FieldHelp>
            <FieldHelp label="Worst-line weight" help="The single worst overage on any one line.">
              <FormField
                control={form.control}
                name="w_worst_bps"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <BpsInput value={field.value} onChange={field.onChange} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </FieldHelp>
            <FieldHelp label="Order value weight" help="Larger orders carry more scrutiny, up to the value reference.">
              <FormField
                control={form.control}
                name="w_value_bps"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <BpsInput value={field.value} onChange={field.onChange} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </FieldHelp>
            <FieldHelp label="Margin shortfall weight" help="How far lines fall below their category's margin floor.">
              <FormField
                control={form.control}
                name="w_margin_bps"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <BpsInput value={field.value} onChange={field.onChange} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </FieldHelp>
            <FieldHelp label="Overage scale" help="Points of overage that alone max out a component (default 10.0%).">
              <FormField
                control={form.control}
                name="scale_overage_bps"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <BpsInput value={field.value} onChange={field.onChange} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </FieldHelp>
            <FieldHelp label="Value reference" help="Order size treated as 100% of the value factor.">
              <FormField
                control={form.control}
                name="value_reference_minor"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <MoneyInput value={field.value} onChange={field.onChange} currency="INR" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </FieldHelp>
            <FieldHelp label="Margin scale" help="Margin shortfall (bps) that alone maxes out the margin factor.">
              <FormField
                control={form.control}
                name="margin_scale_bps"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <BpsInput value={field.value} onChange={field.onChange} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </FieldHelp>
          </div>
        </section>

        <section className="space-y-3">
          <div>
            <h3 className="text-sm font-semibold">Thresholds</h3>
            <p className="text-xs text-muted-foreground">
              Where the score routes to no approval, Sales Manager, or Sales Manager + Finance.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <FieldHelp label="L1 required at" help="Score at or above this needs Sales Manager approval.">
              <FormField
                control={form.control}
                name="t1_l1_required"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <Input type="number" min={0} max={100} {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </FieldHelp>
            <FieldHelp label="L2 required at" help="Score at or above this also needs Finance approval.">
              <FormField
                control={form.control}
                name="t2_l2_required"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <Input type="number" min={0} max={100} {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </FieldHelp>
            <FieldHelp label="Hard breach" help="Overage past a line's own ceiling that forces a minimum L1, regardless of score.">
              <FormField
                control={form.control}
                name="hard_breach_bps"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <BpsInput value={field.value} onChange={field.onChange} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </FieldHelp>
            <FieldHelp label="Finance value floor" help="Orders above this value always require Finance too, regardless of score.">
              <FormField
                control={form.control}
                name="finance_value_floor_minor"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <MoneyInput value={field.value} onChange={field.onChange} currency="INR" />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </FieldHelp>
          </div>
        </section>

        <section className="space-y-3">
          <div>
            <h3 className="text-sm font-semibold">Upsell ranking</h3>
            <p className="text-xs text-muted-foreground">
              How suggested add-ons are scored and filtered in the quote builder.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <FieldHelp label="Minimum margin" help="Candidates below this margin at list price are never suggested.">
              <FormField
                control={form.control}
                name="upsell_min_margin_bps"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <BpsInput value={field.value} onChange={field.onChange} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </FieldHelp>
            <FieldHelp label="Lift weight" help="How much co-purchase affinity drives the ranking.">
              <FormField
                control={form.control}
                name="upsell_w_lift_bps"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <BpsInput value={field.value} onChange={field.onChange} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </FieldHelp>
            <FieldHelp label="Margin weight" help="How much the margin delta drives the ranking.">
              <FormField
                control={form.control}
                name="upsell_w_margin_bps"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <BpsInput value={field.value} onChange={field.onChange} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </FieldHelp>
            <FieldHelp label="Promotion weight" help="Bonus given to promoted products.">
              <FormField
                control={form.control}
                name="upsell_w_promo_bps"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <BpsInput value={field.value} onChange={field.onChange} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </FieldHelp>
          </div>
        </section>

        <section className="space-y-3">
          <div>
            <h3 className="text-sm font-semibold">Anomaly detection &amp; stalled deals</h3>
          </div>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <FieldHelp label="Sigma multiplier (σ)" help="A discount this many standard deviations above a rep's own average is flagged.">
              <FormField
                control={form.control}
                name="sigma_multiplier_x10"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <Input type="number" step={0.1} min={0} {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </FieldHelp>
            <FieldHelp label="Minimum sample size" help="A rep needs at least this many quotes before anomaly detection applies.">
              <FormField
                control={form.control}
                name="min_sample_size"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <Input type="number" min={1} {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </FieldHelp>
            <FieldHelp label="Stalled after (days)" help="A deal with no activity for this long is flagged as stalled.">
              <FormField
                control={form.control}
                name="stalled_after_days"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <Input type="number" min={1} {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </FieldHelp>
          </div>
        </section>

        <div className="flex justify-end gap-2 border-t pt-4">
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button type="submit" disabled={createVersion.isPending}>
            {createVersion.isPending && <Loader2 className="animate-spin" />}
            Save as new draft version
          </Button>
        </div>
      </form>
    </Form>
  );
}
