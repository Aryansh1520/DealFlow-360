"use client";

import * as React from "react";

import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";

interface BpsInputProps
  extends Omit<React.ComponentProps<"input">, "value" | "onChange" | "type"> {
  /** Basis points — the wire value (1250 == 12.5%). */
  value: number;
  /** Emits basis points. */
  onChange: (bps: number) => void;
  /** Optional lower / upper bound, in basis points. Values outside are clamped
   * before they're emitted (and the field snaps to the bound on blur). */
  minBps?: number;
  maxBps?: number;
}

/**
 * A human-facing percentage that emits/accepts basis points. Every discount,
 * ceiling and tax field in a form uses this — `FRONTEND_PHASE_1.md` Task 7.
 */
export const BpsInput = React.forwardRef<HTMLInputElement, BpsInputProps>(
  ({ value, onChange, className, minBps, maxBps, ...props }, ref) => {
    const [text, setText] = React.useState(() => (value / 100).toString());
    const focused = React.useRef(false);

    const clamp = React.useCallback(
      (bps: number) => {
        let v = bps;
        if (minBps != null) v = Math.max(minBps, v);
        if (maxBps != null) v = Math.min(maxBps, v);
        return v;
      },
      [minBps, maxBps]
    );

    React.useEffect(() => {
      if (!focused.current) setText((value / 100).toString());
    }, [value]);

    return (
      <div className="relative">
        <Input
          ref={ref}
          inputMode="decimal"
          className={cn("pr-8 text-right tabular-nums", className)}
          value={text}
          onFocus={() => {
            focused.current = true;
          }}
          onChange={(event) => {
            const raw = event.target.value;
            setText(raw);
            const parsed = Number(raw);
            if (raw !== "" && !Number.isNaN(parsed)) onChange(clamp(Math.round(parsed * 100)));
          }}
          onBlur={() => {
            focused.current = false;
            const clamped = clamp(Math.round((Number(text) || 0) * 100));
            setText((clamped / 100).toString());
            onChange(clamped);
          }}
          {...props}
        />
        <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-sm text-muted-foreground">
          %
        </span>
      </div>
    );
  }
);
BpsInput.displayName = "BpsInput";
