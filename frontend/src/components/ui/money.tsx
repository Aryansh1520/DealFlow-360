import { formatBps, formatBpsDelta, formatMoney } from "@/lib/money";
import { cn } from "@/lib/utils";

interface MoneyProps {
  minor: number;
  currency: string;
  compact?: boolean;
  className?: string;
}

/** Renders a `_minor` amount. This and `<Bps>` are the only places allowed to
 * divide a money or bps field for display — components never call the
 * formatters inline, keeping the money-arithmetic guard (`npm run check:money`)
 * clean. */
export function Money({ minor, currency, compact, className }: MoneyProps) {
  return (
    <span className={cn("tabular-nums", className)}>
      {formatMoney(minor, currency, { compact })}
    </span>
  );
}

interface BpsProps {
  value: number;
  delta?: boolean;
  dp?: number;
  className?: string;
}

export function Bps({ value, delta, dp, className }: BpsProps) {
  return (
    <span className={cn("tabular-nums", className)}>
      {delta ? formatBpsDelta(value) : formatBps(value, { dp })}
    </span>
  );
}
