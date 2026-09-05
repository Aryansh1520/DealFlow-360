/**
 * Longer, plain-language explanations for every policy field, surfaced as a
 * hover tooltip via `FieldHelp`. Kept in one place so `PolicyForm` (editable)
 * and `PolicyView` (read-only) never drift apart on wording. Source of truth
 * for the underlying mechanics: `context/DECISION_ENGINE.md` §2/§3.
 */
export const POLICY_FIELD_TOOLTIPS = {
  tierCeiling:
    "The flat maximum discount this loyalty tier allows on any line, before any category-specific rule is applied.",
  categoryCeiling:
    "The maximum discount allowed on lines in this category. Whichever is stricter — this or the customer's tier ceiling — wins for a given line.",
  categoryMarginFloor:
    "The minimum acceptable margin % for a line in this category. Falling short of this — even while staying under the discount ceiling — feeds the \"Margin shortfall weight\" part of the risk score.",

  w_blended_bps:
    "Every line's overage (discount points past its own ceiling) is averaged across the whole quote, weighted by how much each line is worth. A ₹500 line 20 points over barely moves this; a ₹4,00,000 line 5 points over moves it a lot. At 45%, this is normally the single biggest factor in the score.",
  w_worst_bps:
    "Looks at only the single worst line on the quote, ignoring everything else. This is what catches a rep burying one badly-discounted line inside an otherwise clean order.",
  w_value_bps:
    "Bigger orders get more scrutiny even with zero policy violations. An order at the \"Value reference\" amount maxes out this factor; smaller orders contribute proportionally less.",
  w_margin_bps:
    "Tracks how far lines fall below their category's own margin floor, weighted by each line's share of the order. A discount can be within its ceiling and still shrink margin below the floor — this is what catches that.",
  scale_overage_bps:
    "The \"full marks\" line for the two overage weights above. At 10 points, a line (or blend) that's already 10 points over its ceiling maxes out that component — more overage past that doesn't add extra risk on paper.",
  value_reference_minor:
    "The order size that counts as 100% risky on the value factor. An order at exactly this amount maxes out the value component regardless of its discounts.",
  margin_scale_bps:
    "Same idea as \"Overage scale\" but for margin shortfall — the amount of margin gap (weighted across lines) that alone maxes out the margin component.",

  t1_l1_required:
    "Once the 0–100 risk score reaches this number, the quote can no longer auto-approve — a Sales Manager has to sign off before it moves forward.",
  t2_l2_required:
    "Once the score reaches this (higher) number, Finance has to approve too, on top of the Sales Manager. This is an additional gate, not a replacement.",
  hard_breach_bps:
    "A safety net that ignores the score entirely: if any single line is discounted more than this many points past its own ceiling, Sales Manager approval is forced no matter how low the overall score is.",
  finance_value_floor_minor:
    "Another score-independent gate: any order whose total value is above this amount needs Finance review — even a perfectly policy-compliant order with a near-zero risk score.",

  upsell_min_margin_bps:
    "A hard floor, not a ranking factor: any product whose margin at full list price falls below this is never suggested as an add-on at all, no matter how well it would sell.",
  upsell_w_lift_bps:
    "How much \"customers who bought X also bought this\" data carries in ranking suggested add-ons — a high-lift product is frequently bought alongside what's already on the quote.",
  upsell_w_margin_bps:
    "How much the margin the add-on would bring in matters to its ranking — a highly profitable add-on gets pushed up the suggestion list.",
  upsell_w_promo_bps:
    "A flat bonus added to any product marked as promoted, nudging it up the suggestion list regardless of lift or margin.",

  sigma_multiplier_x10:
    "Compares a rep's discount on this quote to their own historical average. At 2.0σ, a discount has to be an unusually large jump above what that rep normally gives before it's flagged — not just any discount above policy.",
  min_sample_size:
    "Anomaly detection needs a track record to compare against. A rep with fewer than this many past quotes doesn't have a reliable average yet, so their discounts aren't flagged until they do.",
  stalled_after_days:
    "If nobody touches a quote — no edits, no status change — for this many days, it gets flagged as stalled so a manager can follow up.",
} as const;
