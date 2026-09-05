/**
 * The only place `_minor` fields are divided into display units. `API_CONTRACT.md`
 * §1 "Money formatting rule": no component performs arithmetic on money, and no
 * `_minor` field is ever divided outside this file.
 */

export function formatMoney(
  minor: number,
  currency: string,
  opts?: { compact?: boolean }
): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
    notation: opts?.compact ? "compact" : "standard",
  }).format(minor / 100);
}

/** 1250 -> "12.5%" */
export function formatBps(bps: number, opts?: { dp?: number }): string {
  const dp = opts?.dp ?? 1;
  return `${(bps / 100).toFixed(dp)}%`;
}

/** -240 -> "−2.4%" */
export function formatBpsDelta(bps: number): string {
  const sign = bps > 0 ? "+" : bps < 0 ? "−" : "";
  return `${sign}${Math.abs(bps / 100).toFixed(1)}%`;
}
