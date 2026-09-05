/**
 * A client-side port of `DECISION_ENGINE.md` §3–§4, used only while backend
 * Phase 2's real engine is still `501` (see `USE_MOCKS` in `src/lib/config.ts`).
 *
 * This is **not** fake data dressed up — it runs the documented formula
 * exactly, against the real, live catalogue and policy (fetched from the
 * already-shipped Phase 1 backend). Only the quotation/line/event/approval
 * *persistence* is mocked; the pricing math is real. Delete this file the
 * moment `POST /quotations/{id}/preview` is real — the UI never imports it
 * directly, only `mock/quotations.ts` does, so the swap is contained there.
 *
 * Integer/bps arithmetic throughout, matching the money conventions in
 * `API_CONTRACT.md` §1 — no floats in the money path. `lift`-style ratios
 * aside (none here), everything is `number` holding an integer.
 */
import type { PolicyRead, ProductRead, ProductVariantRead } from "@/lib/api/types";

export interface EngineLineInput {
  /** `null` for a not-yet-persisted line — mirrors `PreviewRequest`. */
  lineId: number | null;
  product: ProductRead;
  variant: ProductVariantRead | null;
  quantity: number;
  discountBps: number;
}

export interface EngineLineResult {
  lineId: number | null;
  productId: number;
  productName: string;
  categoryId: number;
  categoryName: string;
  variantId: number | null;
  quantity: number;
  unitPriceMinor: number;
  discountBps: number;
  netMinor: number;
  taxMinor: number;
  costMinor: number;
  marginMinor: number;
  marginBps: number;
  ceilingBps: number;
  ceilingSource: "tier" | "category";
  tierCeilingBps: number;
  categoryCeilingBps: number;
  overageBps: number;
  marginFloorBps: number;
}

export interface EngineResult {
  lines: EngineLineResult[];
  computation: {
    gross_minor: number;
    discount_total_minor: number;
    net_minor: number;
    tax_minor: number;
    total_minor: number;
    cost_total_minor: number;
    margin_minor: number;
    margin_bps: number;
    effective_discount_bps: number;
    blended_overage_bps: number;
    worst_overage_bps: number;
    risk_score: number;
    required_approvals: ("l1_sales_manager" | "l2_finance")[];
    currency: string;
  };
  trace: {
    policy_version: number;
    customer_tier: string;
    tier_ceiling_bps: number;
    lines: {
      line_id: number | null;
      product_name: string;
      category_name: string;
      discount_bps: number;
      tier_ceiling_bps: number;
      category_ceiling_bps: number;
      effective_ceiling_bps: number;
      ceiling_source: "tier" | "category";
      overage_bps: number;
      weight_bps: number;
      weighted_overage_bps: number;
      margin_bps: number;
      margin_floor_bps: number;
      margin_shortfall_bps: number;
      verdict: "within_limit" | "over_limit" | "hard_breach";
    }[];
    components: {
      key: "blended" | "worst" | "value" | "margin";
      label: string;
      raw_value: number;
      normalised: number;
      weight_bps: number;
      contribution: number;
      explanation: string;
    }[];
    risk_score: number;
    thresholds: Record<string, number>;
    rules_fired: {
      code: string;
      severity: "info" | "warn" | "block";
      message: string;
      line_id: number | null;
    }[];
    required_approvals: string[];
    outcome: "auto_approved" | "l1_required" | "l1_l2_required" | "blocked";
    summary: string;
  };
  /** Hard Gate 1 — any line sells below cost. Submit must reject with
   * `POLICY_VIOLATION`; preview still returns the trace so the builder can
   * show *why* it's blocked. */
  belowCost: boolean;
}

function roundHalfUp(value: number): number {
  return Math.floor(value + 0.5);
}

function bps(numerator: number, denominatorBps: number): number {
  return Math.floor((numerator * 10000) / denominatorBps);
}

export function evaluate(
  lines: EngineLineInput[],
  policy: PolicyRead,
  customerTier: string,
  orderDiscountBps: number
): EngineResult {
  const tierCeiling =
    policy.tier_ceilings.find((tc) => tc.tier === customerTier)?.ceiling_bps ?? 0;

  // Step 1–3: per-line ceiling, overage, and economics. Order-level discount
  // is folded additively into each line's own discount before evaluation —
  // a simplification of the real engine's `distribute_largest_remainder`
  // pushdown (BACKEND_PHASE_2.md Task 1), fine for a mock: line sums still
  // reconcile exactly to the order total.
  const lineResults: EngineLineResult[] = lines.map((line) => {
    const categoryCeiling =
      policy.category_ceilings.find((cc) => cc.category_id === line.product.category_id)
        ?.ceiling_bps ?? 0;
    const marginFloor =
      policy.category_ceilings.find((cc) => cc.category_id === line.product.category_id)
        ?.margin_floor_bps ?? 0;

    const effectiveCeiling = Math.min(tierCeiling, categoryCeiling);
    const ceilingSource: "tier" | "category" = tierCeiling <= categoryCeiling ? "tier" : "category";

    const effectiveDiscountBps = Math.min(10000, line.discountBps + orderDiscountBps);
    const overageBps = Math.max(0, effectiveDiscountBps - effectiveCeiling);

    const unitPrice = line.product.list_price_minor + (line.variant?.extra_price_minor ?? 0);
    const gross = line.quantity * unitPrice;
    const net = roundHalfUp((gross * (10000 - effectiveDiscountBps)) / 10000);
    const cost = line.quantity * line.product.cost_price_minor;
    const margin = net - cost;
    const marginBps = net === 0 ? 0 : Math.floor((margin * 10000) / net);
    const tax = roundHalfUp((net * line.product.tax_bps) / 10000);

    return {
      lineId: line.lineId,
      productId: line.product.id,
      productName: line.product.name,
      categoryId: line.product.category_id,
      categoryName: line.product.category_name,
      variantId: line.variant?.id ?? null,
      quantity: line.quantity,
      unitPriceMinor: unitPrice,
      discountBps: effectiveDiscountBps,
      netMinor: net,
      taxMinor: tax,
      costMinor: cost,
      marginMinor: margin,
      marginBps,
      ceilingBps: effectiveCeiling,
      ceilingSource,
      tierCeilingBps: tierCeiling,
      categoryCeilingBps: categoryCeiling,
      overageBps,
      marginFloorBps: marginFloor,
    };
  });

  const grossTotal = lineResults.reduce((sum, l) => sum + l.quantity * l.unitPriceMinor, 0);
  const netTotal = lineResults.reduce((sum, l) => sum + l.netMinor, 0);
  const taxTotal = lineResults.reduce((sum, l) => sum + l.taxMinor, 0);
  const costTotal = lineResults.reduce((sum, l) => sum + l.costMinor, 0);
  const marginTotal = netTotal - costTotal;
  const marginBpsTotal = netTotal === 0 ? 0 : Math.floor((marginTotal * 10000) / netTotal);
  const discountTotal = grossTotal - netTotal;
  const effectiveDiscountBps = grossTotal === 0 ? 0 : bps(discountTotal, grossTotal);

  // Step 4: revenue weight per line.
  const weights = lineResults.map((l) => (netTotal === 0 ? 0 : l.netMinor / netTotal));

  // Step 5: the two overage aggregates.
  const blendedOverageBps =
    netTotal === 0
      ? 0
      : Math.round(lineResults.reduce((sum, l, i) => sum + l.overageBps * weights[i], 0));
  const worstOverageBps = lineResults.reduce((max, l) => Math.max(max, l.overageBps), 0);

  // Step 6: value and margin factors.
  const { weights: W, thresholds: TH } = policy;
  const valueFactor = Math.min(100, (netTotal * 100) / W.value_reference_minor);
  const marginShortfallBps = lineResults.reduce(
    (sum, l, i) => sum + Math.max(0, l.marginFloorBps - l.marginBps) * weights[i],
    0
  );
  const marginFactor = Math.min(100, (marginShortfallBps * 100) / W.margin_scale_bps);

  // Step 7: the score.
  const blendedComponent =
    (W.w_blended_bps / 10000) * Math.min(100, (blendedOverageBps * 100) / W.scale_overage_bps);
  const worstComponent =
    (W.w_worst_bps / 10000) * Math.min(100, (worstOverageBps * 100) / W.scale_overage_bps);
  const valueComponent = (W.w_value_bps / 10000) * valueFactor;
  const marginComponent = (W.w_margin_bps / 10000) * marginFactor;
  const riskScore = Math.min(100, Math.max(0, Math.round(
    blendedComponent + worstComponent + valueComponent + marginComponent
  )));

  // Step 8: routing.
  const belowCost = lineResults.some((l) => l.marginBps < 0);
  const rulesFired: EngineResult["trace"]["rules_fired"] = [];
  const requiredSet = new Set<string>();

  for (const line of lineResults) {
    if (line.overageBps > 0) {
      rulesFired.push({
        code: line.ceilingSource === "tier" ? "TIER_CEILING_BREACH" : "LINE_CEILING_BREACH",
        severity: line.overageBps > TH.hard_breach_bps ? "block" : "warn",
        message: `${line.productName} is discounted ${(line.overageBps / 100).toFixed(1)} points above its ${(line.ceilingBps / 100).toFixed(1)}% ${line.categoryName} ceiling.`,
        line_id: line.lineId,
      });
    }
    if (line.marginFloorBps - line.marginBps > 0) {
      rulesFired.push({
        code: "MARGIN_FLOOR_BREACH",
        severity: "info",
        message: `${line.productName}'s margin is ${((line.marginFloorBps - line.marginBps) / 100).toFixed(1)} points under the ${line.categoryName} floor.`,
        line_id: line.lineId,
      });
    }
  }

  if (blendedOverageBps > 0 && worstOverageBps <= TH.hard_breach_bps) {
    rulesFired.push({
      code: "BLENDED_THRESHOLD",
      severity: "warn",
      message: `Revenue-weighted overage across ${lineResults.length} line${lineResults.length === 1 ? "" : "s"} is ${(blendedOverageBps / 100).toFixed(1)} points.`,
      line_id: null,
    });
  }

  if (worstOverageBps > TH.hard_breach_bps) {
    rulesFired.push({
      code: "HARD_BREACH_OVERRIDE",
      severity: "block",
      message: `An individual line is ${(worstOverageBps / 100).toFixed(1)} points over its ceiling — ${(TH.hard_breach_bps / 100).toFixed(1)} points forces Sales Manager review regardless of score.`,
      line_id: null,
    });
    requiredSet.add("l1_sales_manager");
  }

  if (netTotal > TH.finance_value_floor_minor) {
    rulesFired.push({
      code: "ORDER_VALUE_FLOOR",
      severity: "block",
      message: `Order value exceeds the ₹${(TH.finance_value_floor_minor / 100).toLocaleString("en-IN")} finance review floor.`,
      line_id: null,
    });
    requiredSet.add("l1_sales_manager");
    requiredSet.add("l2_finance");
  }

  if (riskScore >= TH.t1_l1_required) requiredSet.add("l1_sales_manager");
  if (riskScore >= TH.t2_l2_required) requiredSet.add("l2_finance");

  const requiredApprovals = ["l1_sales_manager", "l2_finance"].filter((r) => requiredSet.has(r));

  let outcome: EngineResult["trace"]["outcome"] = "auto_approved";
  if (belowCost) outcome = "blocked";
  else if (requiredApprovals.includes("l2_finance")) outcome = "l1_l2_required";
  else if (requiredApprovals.includes("l1_sales_manager")) outcome = "l1_required";

  const worstLine = lineResults.reduce(
    (worst, l) => (l.overageBps > (worst?.overageBps ?? -1) ? l : worst),
    null as EngineLineResult | null
  );

  let summary: string;
  if (belowCost) {
    const line = lineResults.find((l) => l.marginBps < 0)!;
    summary = `${line.productName} is priced below cost. This must be fixed before submitting.`;
  } else if (worstLine && worstLine.overageBps > 0) {
    const approvalPhrase =
      outcome === "l1_l2_required"
        ? "Sales Manager and Finance approval required"
        : outcome === "l1_required"
          ? "Sales Manager approval required"
          : "auto-approved";
    summary = `${worstLine.productName} is discounted ${(worstLine.overageBps / 100).toFixed(1)} points above its ${(worstLine.ceilingBps / 100).toFixed(1)}% ${worstLine.categoryName} ceiling. Risk ${riskScore}/100 — ${approvalPhrase}.`;
  } else if (requiredApprovals.length > 0) {
    summary = `All lines within policy, but order value ₹${(netTotal / 100).toLocaleString("en-IN")} exceeds the ₹${(TH.finance_value_floor_minor / 100).toLocaleString("en-IN")} finance review floor.`;
  } else {
    summary = `All lines within policy. Risk ${riskScore}/100 — auto-approved.`;
  }

  const components: EngineResult["trace"]["components"] = [
    {
      key: "blended",
      label: `Blended overage across ${lineResults.length} line${lineResults.length === 1 ? "" : "s"}`,
      raw_value: blendedOverageBps,
      normalised: Math.min(100, (blendedOverageBps * 100) / W.scale_overage_bps),
      weight_bps: W.w_blended_bps,
      contribution: Math.round(blendedComponent * 100) / 100,
      explanation: `Revenue-weighted average overage is ${(blendedOverageBps / 100).toFixed(1)} points.`,
    },
    {
      key: "worst",
      label: "Worst single-line overage",
      raw_value: worstOverageBps,
      normalised: Math.min(100, (worstOverageBps * 100) / W.scale_overage_bps),
      weight_bps: W.w_worst_bps,
      contribution: Math.round(worstComponent * 100) / 100,
      explanation: worstLine
        ? `${worstLine.productName} is ${(worstOverageBps / 100).toFixed(1)} points over its ceiling.`
        : "No line exceeds its ceiling.",
    },
    {
      key: "value",
      label: "Order value",
      raw_value: netTotal,
      normalised: valueFactor,
      weight_bps: W.w_value_bps,
      contribution: Math.round(valueComponent * 100) / 100,
      explanation: `Order is ${valueFactor.toFixed(1)}% of the ₹${(W.value_reference_minor / 100).toLocaleString("en-IN")} value reference.`,
    },
    {
      key: "margin",
      label: "Margin shortfall",
      raw_value: Math.round(marginShortfallBps),
      normalised: marginFactor,
      weight_bps: W.w_margin_bps,
      contribution: Math.round(marginComponent * 100) / 100,
      explanation:
        marginShortfallBps > 0
          ? `Margin is ${(marginShortfallBps / 100).toFixed(1)} points under category floors on a revenue-weighted basis.`
          : "No line is under its category's margin floor.",
    },
  ];

  return {
    lines: lineResults,
    belowCost,
    computation: {
      gross_minor: grossTotal,
      discount_total_minor: discountTotal,
      net_minor: netTotal,
      tax_minor: taxTotal,
      total_minor: netTotal + taxTotal,
      cost_total_minor: costTotal,
      margin_minor: marginTotal,
      margin_bps: marginBpsTotal,
      effective_discount_bps: effectiveDiscountBps,
      blended_overage_bps: blendedOverageBps,
      worst_overage_bps: worstOverageBps,
      risk_score: riskScore,
      required_approvals: requiredApprovals as ("l1_sales_manager" | "l2_finance")[],
      currency: lines[0]?.product.currency ?? "INR",
    },
    trace: {
      policy_version: policy.version,
      customer_tier: customerTier,
      tier_ceiling_bps: tierCeiling,
      lines: lineResults.map((l, i) => ({
        line_id: l.lineId,
        product_name: l.productName,
        category_name: l.categoryName,
        discount_bps: l.discountBps,
        tier_ceiling_bps: l.tierCeilingBps,
        category_ceiling_bps: l.categoryCeilingBps,
        effective_ceiling_bps: l.ceilingBps,
        ceiling_source: l.ceilingSource,
        overage_bps: l.overageBps,
        weight_bps: Math.round(weights[i] * 10000),
        weighted_overage_bps: Math.round(l.overageBps * weights[i]),
        margin_bps: l.marginBps,
        margin_floor_bps: l.marginFloorBps,
        margin_shortfall_bps: Math.max(0, l.marginFloorBps - l.marginBps),
        verdict:
          l.overageBps > TH.hard_breach_bps
            ? "hard_breach"
            : l.overageBps > 0
              ? "over_limit"
              : "within_limit",
      })),
      components,
      risk_score: riskScore,
      thresholds: { t1: TH.t1_l1_required, t2: TH.t2_l2_required },
      rules_fired: rulesFired,
      required_approvals: requiredApprovals,
      outcome,
      summary,
    },
  };
}
