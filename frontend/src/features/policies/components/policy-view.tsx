import { Info } from "lucide-react";

import { Bps, Money } from "@/components/ui/money";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { PolicyRead } from "@/lib/api/types";
import { FieldHelp } from "@/features/policies/components/field-help";
import { POLICY_FIELD_TOOLTIPS as T } from "@/features/policies/field-copy";

/** Small (i) affordance for a table column header — same idea as `FieldHelp`,
 * just for a `TableHead` instead of a labelled form field. */
function HeaderHelp({ label, tooltip }: { label: string; tooltip: string }) {
  return (
    <span className="inline-flex items-center justify-end gap-1">
      {label}
      <Tooltip delayDuration={200}>
        <TooltipTrigger asChild>
          <button
            type="button"
            className="text-muted-foreground/70 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-full"
            aria-label={`What does "${label}" mean?`}
          >
            <Info className="h-3.5 w-3.5" />
          </button>
        </TooltipTrigger>
        <TooltipContent>{tooltip}</TooltipContent>
      </Tooltip>
    </span>
  );
}

/** Read-only rendering of one policy version — the "this is what's live" view,
 * as distinct from `PolicyForm`, which always creates a new draft. */
export function PolicyView({ policy }: { policy: PolicyRead }) {
  return (
    <div className="space-y-8">
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
                <TableHead className="text-right">
                  <HeaderHelp label="Ceiling" tooltip={T.tierCeiling} />
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {policy.tier_ceilings.map((row) => (
                <TableRow key={row.tier}>
                  <TableCell className="capitalize">{row.tier}</TableCell>
                  <TableCell className="text-right">
                    <Bps value={row.ceiling_bps} />
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
            The stricter of the tier ceiling and a line's category ceiling always wins.
          </p>
        </div>
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Category</TableHead>
                <TableHead className="text-right">
                  <HeaderHelp label="Ceiling" tooltip={T.categoryCeiling} />
                </TableHead>
                <TableHead className="text-right">
                  <HeaderHelp label="Margin floor" tooltip={T.categoryMarginFloor} />
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {policy.category_ceilings.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={3} className="h-16 text-center text-muted-foreground">
                    No category ceilings configured.
                  </TableCell>
                </TableRow>
              ) : (
                policy.category_ceilings.map((row) => (
                  <TableRow key={row.category_id}>
                    <TableCell>{row.category_name}</TableCell>
                    <TableCell className="text-right">
                      <Bps value={row.ceiling_bps} />
                    </TableCell>
                    <TableCell className="text-right">
                      <Bps value={row.margin_floor_bps} />
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </section>

      <section className="space-y-3">
        <h3 className="text-sm font-semibold">Weights</h3>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <FieldHelp label="Blended overage weight" tooltip={T.w_blended_bps}>
            <p className="text-lg font-medium tabular-nums"><Bps value={policy.weights.w_blended_bps} /></p>
          </FieldHelp>
          <FieldHelp label="Worst-line weight" tooltip={T.w_worst_bps}>
            <p className="text-lg font-medium tabular-nums"><Bps value={policy.weights.w_worst_bps} /></p>
          </FieldHelp>
          <FieldHelp label="Order value weight" tooltip={T.w_value_bps}>
            <p className="text-lg font-medium tabular-nums"><Bps value={policy.weights.w_value_bps} /></p>
          </FieldHelp>
          <FieldHelp label="Margin shortfall weight" tooltip={T.w_margin_bps}>
            <p className="text-lg font-medium tabular-nums"><Bps value={policy.weights.w_margin_bps} /></p>
          </FieldHelp>
          <FieldHelp label="Overage scale" tooltip={T.scale_overage_bps}>
            <p className="text-lg font-medium tabular-nums"><Bps value={policy.weights.scale_overage_bps} /></p>
          </FieldHelp>
          <FieldHelp label="Value reference" tooltip={T.value_reference_minor}>
            <p className="text-lg font-medium">
              <Money minor={policy.weights.value_reference_minor} currency="INR" />
            </p>
          </FieldHelp>
          <FieldHelp label="Margin scale" tooltip={T.margin_scale_bps}>
            <p className="text-lg font-medium tabular-nums"><Bps value={policy.weights.margin_scale_bps} /></p>
          </FieldHelp>
        </div>
      </section>

      <section className="space-y-3">
        <h3 className="text-sm font-semibold">Thresholds</h3>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <FieldHelp label="L1 required at" tooltip={T.t1_l1_required}>
            <p className="text-lg font-medium tabular-nums">{policy.thresholds.t1_l1_required}</p>
          </FieldHelp>
          <FieldHelp label="L2 required at" tooltip={T.t2_l2_required}>
            <p className="text-lg font-medium tabular-nums">{policy.thresholds.t2_l2_required}</p>
          </FieldHelp>
          <FieldHelp label="Hard breach" tooltip={T.hard_breach_bps}>
            <p className="text-lg font-medium tabular-nums"><Bps value={policy.thresholds.hard_breach_bps} /></p>
          </FieldHelp>
          <FieldHelp label="Finance value floor" tooltip={T.finance_value_floor_minor}>
            <p className="text-lg font-medium">
              <Money minor={policy.thresholds.finance_value_floor_minor} currency="INR" />
            </p>
          </FieldHelp>
        </div>
      </section>

      <section className="space-y-3">
        <h3 className="text-sm font-semibold">Upsell ranking</h3>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <FieldHelp label="Minimum margin" tooltip={T.upsell_min_margin_bps}>
            <p className="text-lg font-medium tabular-nums"><Bps value={policy.upsell.min_margin_bps} /></p>
          </FieldHelp>
          <FieldHelp label="Lift weight" tooltip={T.upsell_w_lift_bps}>
            <p className="text-lg font-medium tabular-nums"><Bps value={policy.upsell.w_lift_bps} /></p>
          </FieldHelp>
          <FieldHelp label="Margin weight" tooltip={T.upsell_w_margin_bps}>
            <p className="text-lg font-medium tabular-nums"><Bps value={policy.upsell.w_margin_bps} /></p>
          </FieldHelp>
          <FieldHelp label="Promotion weight" tooltip={T.upsell_w_promo_bps}>
            <p className="text-lg font-medium tabular-nums"><Bps value={policy.upsell.w_promo_bps} /></p>
          </FieldHelp>
        </div>
      </section>

      <section className="space-y-3">
        <h3 className="text-sm font-semibold">Anomaly detection &amp; stalled deals</h3>
        <div className="grid grid-cols-1 divide-y divide-border rounded-lg border sm:grid-cols-3 sm:divide-x sm:divide-y-0">
          <div className="p-3">
            <FieldHelp label="Sigma multiplier (σ)" tooltip={T.sigma_multiplier_x10}>
              <p className="text-lg font-medium tabular-nums">
                {(policy.anomaly.sigma_multiplier_bps / 10000).toFixed(1)}σ
              </p>
            </FieldHelp>
          </div>
          <div className="p-3">
            <FieldHelp label="Minimum sample size" tooltip={T.min_sample_size}>
              <p className="text-lg font-medium tabular-nums">{policy.anomaly.min_sample_size}</p>
            </FieldHelp>
          </div>
          <div className="p-3">
            <FieldHelp label="Stalled after (days)" tooltip={T.stalled_after_days}>
              <p className="text-lg font-medium tabular-nums">{policy.stalled_after_days}</p>
            </FieldHelp>
          </div>
        </div>
      </section>
    </div>
  );
}
