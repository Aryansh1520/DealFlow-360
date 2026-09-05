"use client";

import { Badge } from "@/components/ui/badge";
import { Bps } from "@/components/ui/money";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import type { DecisionTrace } from "@/lib/api/types";

const OUTCOME_LABEL: Record<DecisionTrace["outcome"], string> = {
  auto_approved: "Auto-approved",
  l1_required: "Sales Manager approval required",
  l1_l2_required: "Sales Manager + Finance approval required",
  blocked: "Blocked",
};

const OUTCOME_TONE: Record<DecisionTrace["outcome"], "positive" | "warning" | "danger"> = {
  auto_approved: "positive",
  l1_required: "warning",
  l1_l2_required: "warning",
  blocked: "danger",
};

// Categorical shading of one accent, not four arbitrary hues — Task 6's
// "one accent, exactly four semantic tones" rule reserves colour for status,
// so the contribution breakdown uses opacity steps of the accent instead.
const COMPONENT_OPACITY: Record<string, string> = {
  blended: "bg-primary",
  worst: "bg-primary/70",
  value: "bg-primary/45",
  margin: "bg-primary/25",
};

const VERDICT_ROW_TONE: Record<string, string> = {
  within_limit: "",
  over_limit: "bg-warning/10",
  hard_breach: "bg-danger/10",
};

const SEVERITY_VARIANT: Record<string, "info" | "warning" | "danger"> = {
  info: "info",
  warn: "warning",
  block: "danger",
};

/**
 * `DECISION_ENGINE.md` §4 rendered in four blocks. Used both as the builder's
 * "why?" drawer and inline on the approvals detail screen — the same
 * component so approver and rep always look at the identical trace.
 * Computes nothing: every number here is a field on `trace`.
 */
export function DecisionTracePanel({ trace }: { trace: DecisionTrace }) {
  const maxContribution = Math.max(
    1,
    trace.components.reduce((sum, c) => sum + Math.max(0, c.contribution), 0)
  );

  return (
    <TooltipProvider>
      <div className="space-y-6">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={OUTCOME_TONE[trace.outcome]} className="text-sm">
              {OUTCOME_LABEL[trace.outcome]}
            </Badge>
            <span className="text-2xl font-semibold tabular-nums">{trace.risk_score}/100</span>
          </div>
          <p className="text-sm leading-relaxed">{trace.summary}</p>
        </div>

        <div className="space-y-2">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Risk contribution
          </p>
          <div className="flex h-6 w-full overflow-hidden rounded-md border">
            {trace.components.map((component) => (
              <Tooltip key={component.key} delayDuration={150}>
                <TooltipTrigger asChild>
                  <div
                    className={cn(
                      "h-full transition-all",
                      COMPONENT_OPACITY[component.key] ?? "bg-primary/50"
                    )}
                    style={{
                      width: `${Math.max(0, (component.contribution / maxContribution) * 100)}%`,
                    }}
                  />
                </TooltipTrigger>
                <TooltipContent>
                  <p className="font-medium">{component.label}</p>
                  <p>{component.explanation}</p>
                  <p className="mt-1 tabular-nums text-muted-foreground">
                    +{component.contribution.toFixed(1)} points
                  </p>
                </TooltipContent>
              </Tooltip>
            ))}
          </div>
          {/* Threshold ruler: t1/t2 markers on the same 0–100 scale as the bar. */}
          <div className="relative h-4 w-full">
            <div
              className="absolute top-0 h-2.5 w-px bg-muted-foreground/50"
              style={{ left: `${trace.thresholds.t1}%` }}
            />
            <span
              className="absolute top-3 -translate-x-1/2 text-[10px] text-muted-foreground"
              style={{ left: `${trace.thresholds.t1}%` }}
            >
              L1 · {trace.thresholds.t1}
            </span>
            <div
              className="absolute top-0 h-2.5 w-px bg-muted-foreground/50"
              style={{ left: `${trace.thresholds.t2}%` }}
            />
            <span
              className="absolute top-3 -translate-x-1/2 text-[10px] text-muted-foreground"
              style={{ left: `${trace.thresholds.t2}%` }}
            >
              L2 · {trace.thresholds.t2}
            </span>
          </div>
          <div className="flex flex-wrap gap-3 pt-1 text-xs text-muted-foreground">
            {trace.components.map((component) => (
              <span key={component.key} className="flex items-center gap-1.5">
                <span
                  className={cn("h-2 w-2 rounded-sm", COMPONENT_OPACITY[component.key] ?? "bg-primary/50")}
                />
                {component.label}
              </span>
            ))}
          </div>
        </div>

        <div className="space-y-2">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Lines
          </p>
          <div className="overflow-x-auto rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Product</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead className="text-right">Discount</TableHead>
                  <TableHead className="text-right">Tier ceiling</TableHead>
                  <TableHead className="text-right">Category ceiling</TableHead>
                  <TableHead className="text-right">Effective</TableHead>
                  <TableHead className="text-right">Overage</TableHead>
                  <TableHead className="text-right">Weight</TableHead>
                  <TableHead className="text-right">Margin</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {trace.lines.map((line, index) => (
                  <TableRow key={line.line_id ?? index} className={VERDICT_ROW_TONE[line.verdict]}>
                    <TableCell className="font-medium">{line.product_name}</TableCell>
                    <TableCell>{line.category_name}</TableCell>
                    <TableCell className="text-right">
                      <Bps value={line.discount_bps} />
                    </TableCell>
                    <TableCell
                      className={cn(
                        "text-right",
                        line.ceiling_source === "tier" && "font-semibold underline decoration-dotted"
                      )}
                    >
                      <Bps value={line.tier_ceiling_bps} />
                    </TableCell>
                    <TableCell
                      className={cn(
                        "text-right",
                        line.ceiling_source === "category" && "font-semibold underline decoration-dotted"
                      )}
                    >
                      <Bps value={line.category_ceiling_bps} />
                    </TableCell>
                    <TableCell className="text-right font-medium">
                      <Bps value={line.effective_ceiling_bps} />
                    </TableCell>
                    <TableCell className="text-right">
                      {line.overage_bps > 0 ? (
                        <span
                          className={
                            line.verdict === "hard_breach" ? "font-semibold text-danger" : "text-warning"
                          }
                        >
                          +<Bps value={line.overage_bps} />
                        </span>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell className="text-right text-muted-foreground">
                      <Bps value={line.weight_bps} />
                    </TableCell>
                    <TableCell className="text-right">
                      <Bps value={line.margin_bps} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>

        {trace.rules_fired.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Rules fired
            </p>
            <div className="flex flex-wrap gap-2">
              {trace.rules_fired.map((rule, index) => (
                <Badge key={index} variant={SEVERITY_VARIANT[rule.severity] ?? "secondary"}>
                  {rule.message}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </div>
    </TooltipProvider>
  );
}
